import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from api import index as backend


class CoursePriceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "test.db"
        self.enterContext(patch.object(backend, "DB_PATH", self.path))
        self.enterContext(patch.object(backend, "USE_POSTGRES", False))
        self.enterContext(patch.object(backend, "try_sync_course_catalog"))
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("CREATE TABLE cursos (id INTEGER PRIMARY KEY, curso TEXT, ativo INTEGER)")
            connection.execute("INSERT INTO cursos VALUES (27, 'Curso existente', 1)")
            connection.commit()
        backend.init_db()
        self.client = backend.app.test_client()

    def rows(self):
        response = self.client.get("/api/admin/table/cursos")
        self.assertEqual(response.status_code, 200)
        return response.json["items"]

    def save(self, rows):
        return self.client.post("/api/admin/table/cursos", json={"rows": rows})

    def test_migration_preserves_existing_courses_and_is_repeatable(self):
        backend.init_db()
        self.assertEqual(self.rows()[0]["curso"], "Curso existente")
        self.assertIsNone(self.rows()[0]["valor_unitario"])

    def test_price_edits_persist_after_reload_including_zero(self):
        for amount, expected in [("1.234,56", 1234.56), ("45.67", 45.67), (0, 0), ("", None)]:
            with self.subTest(amount=amount):
                rows = self.rows()
                rows[0]["valor_unitario"] = amount
                self.assertEqual(self.save(rows).status_code, 200)
                self.assertEqual(self.rows()[0]["valor_unitario"], expected)

    def test_new_course_price_persists_without_temporary_ui_key(self):
        rows = self.rows() + [{"_tempKey": "tmp_test", "curso": "Curso novo", "valor_unitario": "12,34", "ativo": True}]
        self.assertEqual(self.save(rows).status_code, 200)
        saved = next(row for row in self.rows() if row["curso"] == "Curso novo")
        self.assertEqual(saved["valor_unitario"], 12.34)
        self.assertNotIn("_tempKey", saved)

    def test_invalid_prices_are_rejected_before_any_writes(self):
        original = self.rows()
        for amount in [-1, "-1,00", "1.234", "1,234", "abc", "NaN", "Infinity", "1e3", "12.34,56", True]:
            with self.subTest(amount=amount):
                response = self.save([{"curso": "Invalido", "valor_unitario": amount}])
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.rows(), original)

    def test_dashboard_uses_registered_price_even_for_inactive_courses(self):
        rows = self.rows()
        rows[0].update(valor_unitario=99.5, ativo=False)
        self.assertEqual(self.save(rows).status_code, 200)
        backend.execute("INSERT INTO protocolos (protocolo, curso_id) VALUES (?, ?)", ("TEST-1", 27))
        response = self.client.get("/api/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["protocolos"][0]["valor_unitario"], 99.5)
        self.assertEqual(response.json["cursosPorArea"], [])


if __name__ == "__main__":
    unittest.main()