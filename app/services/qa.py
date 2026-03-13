from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from app.schemas.query import QueryCitation, QueryResponse
from app.services.llm import BaseLLMProvider
from app.services.retrieval import RetrievalService

_PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"
_NO_EVIDENCE_ANSWER = "\uadfc\uac70 \uc5c6\uc74c"


class QAResponseValidationError(Exception):
    """Raised when model output cannot be validated against QA schema."""


class _LLMCitation(BaseModel):
    chunk_id: uuid.UUID
    quote: str = Field(default="")


class _LLMAnswer(BaseModel):
    answer: str
    citations: list[_LLMCitation] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low"]
    needs_human_review: bool


class QAService:
    def __init__(
        self,
        *,
        retrieval_service: RetrievalService,
        llm_provider: BaseLLMProvider,
        default_top_k: int = 5,
        default_lexical_k: int = 20,
        default_semantic_k: int = 20,
        default_prompt_version: Literal["v1", "v2"] = "v1",
    ) -> None:
        self.retrieval_service = retrieval_service
        self.llm_provider = llm_provider
        self.default_top_k = default_top_k
        self.default_lexical_k = default_lexical_k
        self.default_semantic_k = default_semantic_k
        self.default_prompt_version = default_prompt_version

    def answer(
        self,
        *,
        question: str,
        top_k: int | None = None,
        lexical_k: int | None = None,
        semantic_k: int | None = None,
        prompt_version: Literal["v1", "v2"] | None = None,
        document_id: uuid.UUID | None = None,
    ) -> QueryResponse:
        cleaned_question = question.strip()
        if not cleaned_question:
            return self._fallback_response()

        retrieval_result = self.retrieval_service.retrieve(
            query=cleaned_question,
            top_k=top_k or self.default_top_k,
            lexical_k=lexical_k or self.default_lexical_k,
            semantic_k=semantic_k or self.default_semantic_k,
            document_id=document_id,
        )
        if not retrieval_result.chunks:
            return self._fallback_response()

        resolved_prompt_version = prompt_version or self.default_prompt_version
        system_prompt = self._load_prompt(resolved_prompt_version)
        schema_text = self._load_answer_schema()
        evidence = [
            {
                "chunk_id": str(chunk.chunk_id),
                "document_id": str(chunk.document_id),
                "source_filename": chunk.source_filename,
                "title": chunk.title,
                "section_path": chunk.section_path,
                "page_number": chunk.page_number,
                "content": chunk.content,
            }
            for chunk in retrieval_result.chunks
        ]
        user_prompt = (
            "Return JSON strictly matching this schema:\n"
            f"{schema_text}\n\n"
            "Question:\n"
            f"{cleaned_question}\n\n"
            "Evidence:\n"
            f"{json.dumps(evidence, ensure_ascii=False)}"
        )

        llm_output = self.llm_provider.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        parsed = self._parse_model_output(llm_output)

        answer_text = parsed.answer.strip()
        if answer_text == _NO_EVIDENCE_ANSWER:
            return self._fallback_response()

        chunk_by_id = {chunk.chunk_id: chunk for chunk in retrieval_result.chunks}
        citations: list[QueryCitation] = []
        for llm_citation in parsed.citations:
            chunk = chunk_by_id.get(llm_citation.chunk_id)
            if chunk is None:
                return self._fallback_response()

            quote = llm_citation.quote.strip() or chunk.content[:200]
            citations.append(
                QueryCitation(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    source_filename=chunk.source_filename or "",
                    title=chunk.title,
                    section_path=chunk.section_path,
                    page_number=chunk.page_number,
                    quote=quote,
                )
            )

        if not citations:
            return self._fallback_response()

        return QueryResponse(
            answer=answer_text,
            citations=citations,
            confidence=parsed.confidence,
            needs_human_review=parsed.needs_human_review,
        )

    def _load_prompt(self, prompt_version: Literal["v1", "v2"]) -> str:
        prompt_file = _PROMPT_DIR / f"query_answer_{prompt_version}.txt"
        if not prompt_file.exists():
            raise QAResponseValidationError(f"Prompt file not found: {prompt_file}")
        return prompt_file.read_text(encoding="utf-8")

    def _load_answer_schema(self) -> str:
        schema_file = _PROMPT_DIR / "answer_schema.json"
        if not schema_file.exists():
            raise QAResponseValidationError(f"Schema file not found: {schema_file}")
        try:
            parsed_schema = json.loads(schema_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise QAResponseValidationError("Answer schema file is not valid JSON.") from exc
        return json.dumps(parsed_schema, ensure_ascii=False)

    def _parse_model_output(self, payload: str) -> _LLMAnswer:
        body = payload.strip()
        if body.startswith("```"):
            body = body.strip("`")
            body = body.replace("json", "", 1).strip()

        try:
            raw = json.loads(body)
        except json.JSONDecodeError:
            left = body.find("{")
            right = body.rfind("}")
            if left == -1 or right == -1 or right <= left:
                raise QAResponseValidationError("Model output is not valid JSON.") from None
            try:
                raw = json.loads(body[left : right + 1])
            except json.JSONDecodeError as exc:
                raise QAResponseValidationError("Model output JSON parsing failed.") from exc

        try:
            return _LLMAnswer.model_validate(raw)
        except ValidationError as exc:
            raise QAResponseValidationError("Model output schema validation failed.") from exc

    def _fallback_response(self) -> QueryResponse:
        return QueryResponse(
            answer=_NO_EVIDENCE_ANSWER,
            citations=[],
            confidence="low",
            needs_human_review=True,
        )
