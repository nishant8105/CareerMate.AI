"""
subjective.py — Backward compatibility wrapper for SubjectiveTest.
Delegates to the modern QuestionGenerator in question_generator.py.
"""

from question_generator import QuestionGenerator

class SubjectiveTest(QuestionGenerator):
    """Legacy wrapper for backward compatibility with Question Predictor 1.0."""
    def __init__(self, data, noOfQues=100, difficulty="medium"):
        super().__init__(data=data, no_of_questions=noOfQues, difficulty=difficulty)
