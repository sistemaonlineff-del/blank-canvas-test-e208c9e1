import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import ts from "typescript";

const source = readFileSync(new URL("../src/courseFinancials.ts", import.meta.url), "utf8");
const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext } });
const { lookupCourseFinancial, normalizeCourseUnitValue, courseFinancialLabel } = await import(
  `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
);

test("preserves legacy prices until a course value is supplied", () => {
  for (const valor_unitario of [undefined, null, "", " "]) {
    assert.equal(lookupCourseFinancial({ id: 27, valor_unitario }).unitValue, 19200);
  }
  assert.equal(lookupCourseFinancial({ id: 999, curso: "Curso novo" }), null);
});

test("registered prices override legacy prices and preserve planned quantities", () => {
  const result = lookupCourseFinancial({ id: 27, valor_unitario: "1234,56" });
  assert.equal(result.unitValue, 1234.56);
  assert.equal(result.plannedQuantity, 20);
  assert.equal(result.source, "Cadastro do curso");
  assert.equal(lookupCourseFinancial({ id: 27, valor_unitario: 0 }).unitValue, 0);
  assert.equal(lookupCourseFinancial({ curso: "Curso novo", valor_unitario: 10.5 }).unitValue, 10.5);
  assert.match(courseFinancialLabel({ valor_unitario: 10.5 }), /10,50/);
});

test("accepts cents and Brazilian decimal input", () => {
  for (const value of [1234.56, "1234.56", "1234,56", "1.234,56", " 1234,56 "]) {
    assert.equal(normalizeCourseUnitValue(value), 1234.56);
  }
  assert.equal(normalizeCourseUnitValue("0"), 0);
  assert.equal(normalizeCourseUnitValue(""), null);
});

test("rejects negative, malformed and excessive precision values", () => {
  for (const value of [-1, "-1,00", "1.234", "1,234", "abc", "NaN", Infinity, "1e3", "12.34,56", true]) {
    assert.throws(() => normalizeCourseUnitValue(value), /valor unitário/);
    assert.equal(lookupCourseFinancial({ id: 27, valor_unitario: value }), null);
  }
});