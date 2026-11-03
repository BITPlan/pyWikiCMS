"""
Created on 2026-11-03

@author: wf

spam protection of the forms without a third party: a challenge field asks a
question whose expected answer stays server side under the form token,
see https://github.com/BITPlan/pyWikiCMS/issues/42
"""

import secrets
import time
from dataclasses import dataclass
from typing import ClassVar, Dict, Optional, Tuple


@dataclass
class Challenge:
    """
    an issued challenge: the question shown and the answer kept
    """

    token: str
    question: str
    answer: str
    expires: float

    @property
    def expired(self) -> bool:
        """
        True once the lifetime is over
        """
        is_expired = time.time() > self.expires
        return is_expired


class FormChallenge:
    """
    issue and check challenges; the store lives in the process memory,
    which fits one frontend process per site
    """

    store: ClassVar[Dict[str, Challenge]] = {}
    kinds: ClassVar[Tuple[str, ...]] = ("arithmetic",)

    @classmethod
    def arithmetic(cls) -> Tuple[str, str]:
        """
        a sum of two small numbers

        Returns:
            Tuple[str, str]: question and expected answer
        """
        a = secrets.randbelow(9) + 1
        b = secrets.randbelow(9) + 1
        question = f"{a} + {b} = ?"
        answer = str(a + b)
        return question, answer

    @classmethod
    def issue(cls, kind: str = "arithmetic", lifetime: int = 600) -> Challenge:
        """
        issue a challenge of the given kind

        Args:
            kind(str): the kind of challenge
            lifetime(int): seconds the challenge stays valid

        Returns:
            Challenge: the issued challenge

        Raises:
            ValueError: for an unknown kind
        """
        if kind not in cls.kinds:
            raise ValueError(f"unknown challenge kind {kind}")
        cls.expire()
        question, answer = cls.arithmetic()
        challenge = Challenge(
            token=secrets.token_hex(16),
            question=question,
            answer=answer,
            expires=time.time() + lifetime,
        )
        cls.store[challenge.token] = challenge
        return challenge

    @classmethod
    def check(cls, token: Optional[str], answer: Optional[str]) -> bool:
        """
        check the answer for the token and consume the token

        Args:
            token(str): the form token of the submission
            answer(str): the answer given

        Returns:
            bool: True if the token is known, not expired and the answer matches
        """
        ok = False
        challenge = cls.store.pop(token, None) if token else None
        if challenge is not None and not challenge.expired:
            ok = (answer or "").strip() == challenge.answer
        return ok

    @classmethod
    def expire(cls) -> None:
        """
        drop expired challenges
        """
        for token in [t for t, c in cls.store.items() if c.expired]:
            cls.store.pop(token, None)
