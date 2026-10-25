import unittest
from unittest.mock import patch
import app

class GradeTests(unittest.TestCase):
    def test_correct(self):
        self.assertTrue(app.grade_sql("sql-001", "SELECT customer,SUM(amount) total FROM orders GROUP BY customer ORDER BY total DESC")["ok"])
    def test_wrong(self):
        self.assertFalse(app.grade_sql("sql-002", "SELECT id, amount FROM orders WHERE amount < 100")["ok"])
    def test_no_mutation(self):
        self.assertFalse(app.grade_sql("sql-002", "DROP TABLE orders")["ok"])
    def test_shared_service_retained(self):
        app.ACTIVE.clear()
        app.ACTIVE.update(["core","analytics"])
        self.assertIn("postgres", app.services_running("analytics"))
        app.ACTIVE.clear()
    def test_no_undeclared_models(self):
        with patch.object(app, "ollama", return_value={"models": [{"name":"example"}]}):
            self.assertIn("not found", app.ai_answer({"model":"unknown","question":"hi","mode":"tutor"})["error"])
if __name__ == "__main__": unittest.main()
