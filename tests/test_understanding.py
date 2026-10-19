"""Deterministic Engineering Understanding Check tests."""

import unittest
from unittest.mock import patch

from campusflow.understanding import QUESTIONS, run_check


class UnderstandingTests(unittest.TestCase):
    def test_questions_are_unique_and_nonempty(self):
        self.assertGreaterEqual(len(QUESTIONS), 5)
        self.assertEqual(len({q for q, _ in QUESTIONS}), len(QUESTIONS))
        for question, guidance in QUESTIONS:
            self.assertTrue(question.strip())
            self.assertTrue(guidance.startswith("Expected:"))

    def test_all_questions_in_order_and_guidance_after_each_answer(self):
        output = []
        prompts = []
        def answer(prompt):
            prompts.append(prompt)
            return "my response"
        run_check(answer, output.append)
        self.assertEqual(len(prompts), len(QUESTIONS))
        for index, (question, guidance) in enumerate(QUESTIONS, 1):
            question_line = f"Question {index}/{len(QUESTIONS)}: {question}"
            self.assertIn(question_line, output)
            self.assertIn(guidance, output)
            self.assertLess(output.index(question_line), output.index(guidance))
        self.assertIn("no score assigned", output[-1])

    def test_quit_does_not_reveal_unanswered_guidance(self):
        output = []
        run_check(lambda _: " QuIt ", output.append)
        self.assertIn("Check ended without grading.", output)
        self.assertNotIn(QUESTIONS[0][1], output)
        self.assertNotIn(QUESTIONS[1][0], " ".join(output))

    def test_exit_on_later_question(self):
        output = []
        answers = iter(["first", "exit"])
        run_check(lambda _: next(answers), output.append)
        self.assertIn(QUESTIONS[0][1], output)
        self.assertNotIn(QUESTIONS[1][1], output)

    def test_eof_exits_cleanly(self):
        output = []
        def eof(_):
            raise EOFError()
        run_check(eof, output.append)
        self.assertEqual(output[-1], "Check ended without grading.")

    def test_keyboard_interrupt_exits_cleanly(self):
        output = []
        def interrupt(_):
            raise KeyboardInterrupt()
        run_check(interrupt, output.append)
        self.assertEqual(output[-1], "Check ended without grading.")

    def test_invalid_input_fn_result_is_programmer_error(self):
        with self.assertRaises(TypeError):
            run_check(lambda _: None, lambda _: None)

    def test_default_functions_work_with_patched_io(self):
        with patch("builtins.input", return_value="quit") as mocked_input, patch("builtins.print") as printer:
            # Default arguments were bound at function definition time.
            # Inject the patched callables explicitly to avoid real stdin/stdout.
            run_check(input_fn=mocked_input, output_fn=printer)
        self.assertTrue(printer.called)
