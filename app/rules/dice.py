"""Dice rolling utilities for Parqués.

This module provides the Dice class to simulate rolling two six-sided dice,
including utility methods for checking pairs.
"""
import random
from typing import Tuple

class Dice:
    """Class to simulate rolling two Parqués dice."""

    @staticmethod
    def roll() -> Tuple[int, int]:
        """Rolls two six-sided dice.

        Returns:
            Tuple[int, int]: A tuple with the results of the two dice.
        """
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        return d1, d2

    @staticmethod
    def are_pairs(d1: int, d2: int) -> bool:
        """Checks if the dice results are a pair.

        Args:
            d1: Result of the first die.
            d2: Result of the second die.

        Returns:
            True if both dice show the same value, False otherwise.
        """
        return d1 == d2