"""Bedrock client helpers for ORRG summarization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, Any, Tuple

import boto3

from new_capability.config.pricing import (
    CLAUDE_INFERENCE_PROFILES,
    PRICING_REGISTRY,
    PRICING_VERSION,
    estimate_request_cost,
)


DEFAULT_REGION = "us-east-1"


@dataclass(frozen=True)
class BedrockUsage:
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    pricing_version: str


def get_profile_options() -> dict[str, str]:
    """Return profile id -> label mapping for UI selection."""
    profile_rows = []
    for profile in CLAUDE_INFERENCE_PROFILES:
        model_key = _get_pricing_key_for_profile(profile.profile_id)
        if model_key and model_key in PRICING_REGISTRY:
            pricing = PRICING_REGISTRY[model_key]
            label = (
                f"{profile.name} "
                f"(${pricing.input_per_1m:.2f}/1M in, ${pricing.output_per_1m:.2f}/1M out)"
            )
            sort_cost = pricing.input_per_1m + pricing.output_per_1m
        else:
            label = f"{profile.name} (pricing TBD)"
            sort_cost = float("inf")
        profile_rows.append((sort_cost, profile.profile_id, label))

    profile_rows.sort(key=lambda row: row[0])
    return {profile_id: label for _, profile_id, label in profile_rows}


def invoke_bedrock(
    prompt: str,
    profile_id: str,
    max_tokens: int = 900,
    temperature: float = 0.2,
    region: str = DEFAULT_REGION,
) -> tuple[str, BedrockUsage | None]:
    """Invoke Bedrock and return the text response plus usage details."""
    client = boto3.client("bedrock-runtime", region_name=region)
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt,
                    }
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    response = client.invoke_model(
        modelId=profile_id,
        body=json.dumps(payload),
    )

    body = json.loads(response.get("body").read())
    output_text = _extract_text(body)
    usage = _extract_usage(body, profile_id)
    return output_text, usage


def _extract_text(payload: dict[str, Any]) -> str:
    content = payload.get("content") or []
    if content:
        text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
        if text_parts:
            return "".join(text_parts).strip()
    return payload.get("output", "") or payload.get("response", "") or ""


def _extract_usage(payload: dict[str, Any], profile_id: str) -> BedrockUsage | None:
    usage = payload.get("usage") or payload.get("metrics") or {}
    input_tokens = int(usage.get("input_tokens") or usage.get("inputTokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("outputTokens") or 0)
    if input_tokens <= 0 and output_tokens <= 0:
        return None

    model_key = _get_pricing_key_for_profile(profile_id)
    estimated_cost = 0.0
    if model_key and model_key in PRICING_REGISTRY:
        estimated_cost = estimate_request_cost(model_key, input_tokens, output_tokens)

    return BedrockUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost_usd=round(estimated_cost, 6),
        pricing_version=PRICING_VERSION,
    )


def _get_pricing_key_for_profile(profile_id: str) -> str | None:
    profile_lower = profile_id.lower()
    if "sonnet-4-5" in profile_lower:
        return "anthropic.claude-sonnet-4-5"
    if "opus-4-5" in profile_lower:
        return "anthropic.claude-opus-4-5"
    if "opus-4-1" in profile_lower:
        return "anthropic.claude-opus-4-1"
    if "sonnet-4" in profile_lower:
        return "anthropic.claude-sonnet-4"
    if "claude-3-haiku" in profile_lower:
        return "anthropic.claude-3-haiku"
    if "claude-3-sonnet" in profile_lower:
        return "anthropic.claude-3-sonnet"
    if "claude-3-opus" in profile_lower:
        return "anthropic.claude-3-opus"
    if "haiku" in profile_lower:
        return "anthropic.claude-haiku-4-5"
    return None