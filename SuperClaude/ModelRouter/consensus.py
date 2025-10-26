"""
Multi-Model Consensus Builder for SuperClaude Framework.

Implements consensus mechanisms for critical decisions using multiple models.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
import hashlib

logger = logging.getLogger(__name__)


class VoteType(Enum):
    """Types of voting mechanisms."""
    MAJORITY = "majority"  # Simple majority
    UNANIMOUS = "unanimous"  # All must agree
    QUORUM = "quorum"  # Minimum number must agree
    WEIGHTED = "weighted"  # Weight-based voting


class Stance(Enum):
    """Model stance for debate-style consensus."""
    FOR = "for"
    AGAINST = "against"
    NEUTRAL = "neutral"


@dataclass
class ModelVote:
    """Individual model's vote/response."""
    model_name: str
    response: Any
    confidence: float  # 0.0-1.0
    reasoning: str
    stance: Optional[Stance] = None
    tokens_used: int = 0
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConsensusResult:
    """Result of consensus building."""
    consensus_reached: bool
    final_decision: Any
    votes: List[ModelVote]
    vote_type: VoteType
    agreement_score: float  # 0.0-1.0
    disagreements: List[Dict[str, Any]]
    synthesis: str
    total_tokens: int
    total_time: float


class ConsensusBuilder:
    """
    Builds multi-model consensus for critical decisions.

    Features:
    - Multiple voting mechanisms
    - Debate-style structured disagreement
    - Weighted voting based on expertise
    - Conflict resolution strategies
    - Result synthesis and aggregation
    """

    def __init__(self, router=None):
        """
        Initialize consensus builder.

        Args:
            router: Optional ModelRouter for model selection
        """
        self.router = router
        self.execution_cache: Dict[str, ConsensusResult] = {}
        self.model_executors: Dict[str, Callable] = {}  # Model name to executor function

    def register_executor(self, model_name: str, executor: Callable) -> None:
        """
        Register a model executor function.

        Args:
            model_name: Name of the model
            executor: Async function that executes the model
        """
        self.model_executors[model_name] = executor

    async def build_consensus(self,
                              prompt: str,
                              models: Optional[List[str]] = None,
                              vote_type: VoteType = VoteType.MAJORITY,
                              quorum_size: int = 2,
                              stances: Optional[Dict[str, Stance]] = None,
                              context: Optional[Dict[str, Any]] = None) -> ConsensusResult:
        """
        Build consensus across multiple models.

        Args:
            prompt: The question/decision to reach consensus on
            models: List of model names (defaults to ensemble from router)
            vote_type: Type of voting mechanism
            quorum_size: Minimum agreements needed for QUORUM vote type
            stances: Optional stance assignments for debate-style consensus
            context: Additional context for models

        Returns:
            ConsensusResult with decision and details
        """
        start_time = datetime.now()

        # Get models from router if not specified
        if not models:
            if self.router:
                models = self.router.get_ensemble(size=3)
            else:
                models = ['gpt-5', 'claude-opus-4.1', 'gpt-4.1']

        # Check cache
        cache_key = self._generate_cache_key(prompt, models, vote_type)
        if cache_key in self.execution_cache:
            logger.debug(f"Returning cached consensus for {cache_key}")
            return self.execution_cache[cache_key]

        # Prepare prompts with stances if specified
        model_prompts = self._prepare_prompts(prompt, models, stances, context)

        # Execute models in parallel
        votes = await self._execute_models_parallel(model_prompts)

        # Analyze votes based on vote type
        consensus_reached, final_decision = self._analyze_votes(votes, vote_type, quorum_size)

        # Identify disagreements
        disagreements = self._identify_disagreements(votes)

        # Calculate agreement score
        agreement_score = self._calculate_agreement_score(votes)

        # Synthesize results
        synthesis = self._synthesize_results(votes, consensus_reached, final_decision)

        # Calculate totals
        total_tokens = sum(vote.tokens_used for vote in votes)
        total_time = (datetime.now() - start_time).total_seconds()

        # Create result
        result = ConsensusResult(
            consensus_reached=consensus_reached,
            final_decision=final_decision,
            votes=votes,
            vote_type=vote_type,
            agreement_score=agreement_score,
            disagreements=disagreements,
            synthesis=synthesis,
            total_tokens=total_tokens,
            total_time=total_time
        )

        # Cache result
        self.execution_cache[cache_key] = result

        return result

    def _normalize_vote_response(self, response: Any) -> str:
        """Normalize vote response for aggregation."""
        if isinstance(response, dict):
            if 'decision' in response:
                return str(response['decision'])
            try:
                return json.dumps(response, sort_keys=True)
            except TypeError:
                return str(response)
        return str(response)

    def _prepare_prompts(self,
                         base_prompt: str,
                         models: List[str],
                         stances: Optional[Dict[str, Stance]],
                         context: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        Prepare model-specific prompts with stances.

        Args:
            base_prompt: Base prompt for all models
            models: List of model names
            stances: Stance assignments
            context: Additional context

        Returns:
            Dictionary of model name to prompt
        """
        prompts = {}

        for model in models:
            prompt_parts = []

            # Add stance instruction if specified
            if stances and model in stances:
                stance = stances[model]
                if stance == Stance.FOR:
                    prompt_parts.append("You are arguing FOR this proposal. "
                                        "Provide strong supporting arguments.")
                elif stance == Stance.AGAINST:
                    prompt_parts.append("You are arguing AGAINST this proposal. "
                                        "Provide strong opposing arguments.")
                else:
                    prompt_parts.append("You are taking a NEUTRAL stance. "
                                        "Provide balanced analysis.")

            # Add context if provided
            if context:
                prompt_parts.append(f"Context: {json.dumps(context, indent=2)}")

            # Add base prompt
            prompt_parts.append(base_prompt)

            # Add structured response request
            prompt_parts.append("\n\nProvide your response with:\n"
                                "1. Your decision/answer\n"
                                "2. Key reasoning points\n"
                                "3. Confidence level (0-100%)\n"
                                "4. Any caveats or concerns")

            prompts[model] = "\n\n".join(prompt_parts)

        return prompts

    async def _execute_models_parallel(self,
                                        model_prompts: Dict[str, str]) -> List[ModelVote]:
        """
        Execute multiple models in parallel.

        Args:
            model_prompts: Dictionary of model name to prompt

        Returns:
            List of ModelVote objects
        """
        tasks = []
        for model_name, prompt in model_prompts.items():
            task = self._execute_single_model(model_name, prompt)
            tasks.append(task)

        # Execute all models in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        votes = []
        for i, (model_name, _) in enumerate(model_prompts.items()):
            if isinstance(results[i], Exception):
                logger.error(f"Model {model_name} failed: {results[i]}")
                # Create failed vote
                vote = ModelVote(
                    model_name=model_name,
                    response=None,
                    confidence=0.0,
                    reasoning=f"Execution failed: {str(results[i])}",
                    tokens_used=0,
                    execution_time=0.0
                )
            else:
                vote = results[i]

            votes.append(vote)

        return votes

    async def _execute_single_model(self, model_name: str, prompt: str) -> ModelVote:
        """
        Execute a single model.

        Args:
            model_name: Name of the model
            prompt: Prompt to execute

        Returns:
            ModelVote with results
        """
        start_time = datetime.now()

        # Use registered executor if available
        if model_name in self.model_executors:
            executor = self.model_executors[model_name]
            try:
                result = await executor(prompt)
                # Parse result (assumes executor returns dict with expected fields)
                return ModelVote(
                    model_name=model_name,
                    response=result.get('response'),
                    confidence=result.get('confidence', 0.8),
                    reasoning=result.get('reasoning', ''),
                    tokens_used=result.get('tokens_used', 0),
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    metadata=result.get('metadata', {})
                )
            except Exception as e:
                logger.error(f"Executor failed for {model_name}: {e}")
                raise

        # Fallback to mock execution (for testing)
        logger.warning(f"No executor registered for {model_name}, using mock response")
        return ModelVote(
            model_name=model_name,
            response=f"Mock response from {model_name}",
            confidence=0.75,
            reasoning="This is a mock response for testing",
            tokens_used=100,
            execution_time=(datetime.now() - start_time).total_seconds()
        )

    def _analyze_votes(self,
                       votes: List[ModelVote],
                       vote_type: VoteType,
                       quorum_size: int) -> Tuple[bool, Any]:
        """
        Analyze votes to determine consensus.

        Args:
            votes: List of model votes
            vote_type: Voting mechanism
            quorum_size: Minimum agreements for quorum

        Returns:
            Tuple of (consensus_reached, final_decision)
        """
        valid_votes = [v for v in votes if v.response is not None]

        if not valid_votes:
            return False, None

        if vote_type == VoteType.UNANIMOUS:
            # All must agree
            responses = [self._normalize_vote_response(v.response) for v in valid_votes]
            if len(set(responses)) == 1:
                return True, valid_votes[0].response
            return False, None

        elif vote_type == VoteType.MAJORITY:
            # Simple majority
            response_counts: Dict[str, int] = {}
            response_map: Dict[str, Any] = {}
            for vote in valid_votes:
                response_key = self._normalize_vote_response(vote.response)
                response_counts[response_key] = response_counts.get(response_key, 0) + 1
                response_map.setdefault(response_key, vote.response)

            # Find majority
            if len(response_counts) == 1:
                response_key = next(iter(response_counts))
                return True, response_map[response_key]
            return False, None

        elif vote_type == VoteType.QUORUM:
            # Minimum number must agree
            response_counts: Dict[str, int] = {}
            response_map: Dict[str, Any] = {}
            for vote in valid_votes:
                response_key = self._normalize_vote_response(vote.response)
                response_counts[response_key] = response_counts.get(response_key, 0) + 1
                response_map.setdefault(response_key, vote.response)

            # Check if any response meets quorum
            for response_key, count in response_counts.items():
                if count >= quorum_size:
                    return True, response_map[response_key]
            return False, None

        elif vote_type == VoteType.WEIGHTED:
            # Weight by confidence
            weighted_responses = {}
            response_map = {}
            total_weight = 0

            for vote in valid_votes:
                response_str = str(vote.response)
                weight = vote.confidence
                weighted_responses[response_str] = weighted_responses.get(response_str, 0) + weight
                total_weight += weight
                if response_str not in response_map:
                    response_map[response_str] = vote.response

            # Find response with highest weight
            if total_weight > 0:
                for response_str, weight in weighted_responses.items():
                    if weight > total_weight / 2:
                        return True, response_map[response_str]

            # Return highest weighted even without majority
            if weighted_responses:
                best_response = max(weighted_responses, key=weighted_responses.get)
                return False, response_map[best_response]

            return False, None

        return False, None

    def _identify_disagreements(self, votes: List[ModelVote]) -> List[Dict[str, Any]]:
        """
        Identify and categorize disagreements.

        Args:
            votes: List of model votes

        Returns:
            List of disagreement details
        """
        disagreements = []
        valid_votes = [v for v in votes if v.response is not None]

        # Group responses
        response_groups = {}
        for vote in valid_votes:
            response_str = str(vote.response)
            if response_str not in response_groups:
                response_groups[response_str] = []
            response_groups[response_str].append(vote)

        # Identify disagreements
        if len(response_groups) > 1:
            for response_str, group_votes in response_groups.items():
                disagreement = {
                    'response': response_str,
                    'models': [v.model_name for v in group_votes],
                    'average_confidence': sum(v.confidence for v in group_votes) / len(group_votes),
                    'reasoning': [v.reasoning for v in group_votes]
                }
                disagreements.append(disagreement)

        return disagreements

    def _calculate_agreement_score(self, votes: List[ModelVote]) -> float:
        """
        Calculate overall agreement score.

        Args:
            votes: List of model votes

        Returns:
            Agreement score (0.0-1.0)
        """
        valid_votes = [v for v in votes if v.response is not None]
        if len(valid_votes) <= 1:
            return 1.0 if valid_votes else 0.0

        # Count unique responses
        unique_responses = len(set(str(v.response) for v in valid_votes))

        # Calculate agreement (inverse of diversity)
        agreement = 1.0 - ((unique_responses - 1) / len(valid_votes))

        # Weight by confidence
        avg_confidence = sum(v.confidence for v in valid_votes) / len(valid_votes)
        weighted_agreement = agreement * avg_confidence

        return weighted_agreement

    def _synthesize_results(self,
                            votes: List[ModelVote],
                            consensus_reached: bool,
                            final_decision: Any) -> str:
        """
        Synthesize results into summary.

        Args:
            votes: List of model votes
            consensus_reached: Whether consensus was reached
            final_decision: The final decision

        Returns:
            Synthesis text
        """
        synthesis_parts = []

        if consensus_reached:
            synthesis_parts.append(f"✅ Consensus reached: {final_decision}")
        else:
            synthesis_parts.append(f"⚠️ No consensus reached")
            if final_decision:
                synthesis_parts.append(f"Closest agreement: {final_decision}")

        # Add model perspectives
        synthesis_parts.append("\nModel perspectives:")
        for vote in votes:
            if vote.response is not None:
                confidence_pct = int(vote.confidence * 100)
                synthesis_parts.append(f"- {vote.model_name} ({confidence_pct}%): {vote.response}")

        # Add key reasoning points
        if any(v.reasoning for v in votes):
            synthesis_parts.append("\nKey reasoning:")
            for vote in votes:
                if vote.reasoning:
                    synthesis_parts.append(f"- {vote.model_name}: {vote.reasoning[:200]}")

        return "\n".join(synthesis_parts)

    def _generate_cache_key(self,
                            prompt: str,
                            models: List[str],
                            vote_type: VoteType) -> str:
        """Generate cache key for consensus result."""
        key_parts = [
            prompt[:100],  # First 100 chars of prompt
            ",".join(sorted(models)),
            vote_type.value
        ]
        key_str = "|".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def debate_consensus(self,
                               topic: str,
                               models: Optional[List[str]] = None,
                               rounds: int = 2) -> ConsensusResult:
        """
        Run debate-style consensus with multiple rounds.

        Args:
            topic: Topic to debate
            models: List of models (assigns stances automatically)
            rounds: Number of debate rounds

        Returns:
            ConsensusResult after debate
        """
        if not models:
            models = ['gpt-5', 'claude-opus-4.1', 'gpt-4.1'] if self.router else []

        # Assign stances
        stances = {}
        for i, model in enumerate(models):
            if i == 0:
                stances[model] = Stance.FOR
            elif i == 1:
                stances[model] = Stance.AGAINST
            else:
                stances[model] = Stance.NEUTRAL

        # Run initial round
        result = await self.build_consensus(
            prompt=f"Debate topic: {topic}",
            models=models,
            vote_type=VoteType.WEIGHTED,
            stances=stances
        )

        # Run additional rounds if no consensus
        current_round = 1
        while current_round < rounds and not result.consensus_reached:
            # Prepare follow-up prompt with previous results
            follow_up = f"Previous round results:\n{result.synthesis}\n\n" \
                        f"Round {current_round + 1}: Respond to other perspectives"

            result = await self.build_consensus(
                prompt=follow_up,
                models=models,
                vote_type=VoteType.WEIGHTED,
                stances=stances
            )
            current_round += 1

        return result
