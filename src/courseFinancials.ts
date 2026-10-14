export type CourseFinancialEntry = {
  unitValue: number;
  plannedQuantity?: number;
  source: string;
  aliases?: string[];
};

type CourseLike = {
  id?: number | string | null;
  curso?: string | null;
  course?: string | null;
  area?: string | null;
  valor_unitario?: number | string | null;
};

const RAW_COURSE_FINANCIALS: Record<number, CourseFinancialEntry> = {
  27: {
    unitValue: 19200,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Adequação de agroindústrias aos Serviços de Inspeção de Produtos de Origem Animal e/ou Vegetal",
      "1. Conformidade Sanitária e Inspeção"
    ]
  },
  28: {
    unitValue: 7490,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Avaliação de Tempo de Vida de Prateleira"]
  },
  29: {
    unitValue: 12000,
    plannedQuantity: 40,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Design de Rótulo e aplicações de elementos gráficos na embalagem"]
  },
  30: {
    unitValue: 3750,
    plannedQuantity: 40,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Rotulagem de Alimentos e Informação Nutricional"]
  },
  31: {
    unitValue: 2240,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Consultoria desenvolvida para atender ao público-alvo",
      "Organização Financeira e Governança Economica"
    ]
  },
  32: {
    unitValue: 3640,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Presença Financeira - Indústria de Alimentos e Agroindústria (Módulo 1 – Gestão do Caixa)"]
  },
  33: {
    unitValue: 2800,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Presença Financeira - Indústria de Alimentos e Agroindústria (Módulo 2 – Formação de Preços e Gestão de Custos)"]
  },
  34: {
    unitValue: 1440,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Planejamento Financeiro",
      "Planejamento Financeiro para Investimentos"
    ]
  },
  35: {
    unitValue: 3960,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Análise de Crédito e Oportunidades de Financiamento",
      "Acesso a credito e Relacionamrnto com instituições financeiras"
    ]
  },
  36: {
    unitValue: 1120,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Consultoria desenvolvida para atender ao público-alvo",
      "Treinamento de Lideranças e Alfabetização Financeira dos Membros"
    ]
  },
  37: {
    unitValue: 5000,
    plannedQuantity: 25,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Implantação de Gestão ESG em conformidade ao Programa de Recomendação ABNT PR 2030"]
  },
  38: {
    unitValue: 7000,
    plannedQuantity: 22,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["Planejamento para Presença Digital e Links Patrocinados"]
  },
  39: {
    unitValue: 19200,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["1. Conformidade Sanitária e Inspeção"]
  },
  43: {
    unitValue: 2240,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["4. Organização Financeira e Governança Econômica"]
  },
  44: {
    unitValue: 3640,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["5.Gestão de Caixa e Planejamento Operacional"]
  },
  45: {
    unitValue: 2800,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["6. Cálculo de Custos e Formação de Preço com Análise de Viabilidade"]
  },
  46: {
    unitValue: 1440,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["7. Planejamento Financeiro para Investimentos"]
  },
  47: {
    unitValue: 3960,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["8. Acesso a Crédito e Relacionamento com Instituições Financeiras"]
  },
  48: {
    unitValue: 1120,
    plannedQuantity: 20,
    source: "Soluções Sebrae valores.xlsx",
    aliases: ["9.Treinamento de Lideranças e Alfabetização Financeira dos Membros"]
  },
  49: {
    unitValue: 5000,
    plannedQuantity: 25,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Desenvolvimento de Negócios",
      "Implantação de Gestão ESG em conformidade ao Programa de Recomendação ABNT PR 2030"
    ]
  },
  50: {
    unitValue: 7000,
    plannedQuantity: 22,
    source: "Soluções Sebrae valores.xlsx",
    aliases: [
      "Mercado",
      "Planejamento para presença Digital e Links Patrocinados"
    ]
  }
};

export function normalizeCourseKey(value: unknown) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function parseCourseId(value: unknown) {
  const id = Number(value);
  return Number.isFinite(id) ? id : null;
}

const NAME_INDEX = Object.entries(RAW_COURSE_FINANCIALS).flatMap(([id, entry]) =>
  (entry.aliases || []).map((alias) => ({
    id: Number(id),
    key: normalizeCourseKey(alias),
    entry
  }))
);

export function normalizeCourseUnitValue(value: unknown): number | null {
  if (value == null || String(value).trim() === "") return null;
  const text = String(value).trim();
  const normalized = text.includes(",") && /^(?:\d+|\d{1,3}(?:\.\d{3})+),\d{1,2}$/.test(text)
    ? text.replace(/\./g, "").replace(",", ".")
    : text;
  const amount = Number(normalized);
  if (!/^\d+(?:\.\d{1,2})?$/.test(normalized) || !Number.isFinite(amount) || amount < 0) {
    throw new Error("Informe um valor unitário válido, maior ou igual a zero, com até duas casas decimais.");
  }
  return amount;
}

function lookupLegacyCourseFinancial(course: CourseLike | string | null | undefined) {
  const row =
    typeof course === "string"
      ? { curso: course }
      : course || {};
  const courseId = parseCourseId((row as CourseLike).id);
  if (courseId && RAW_COURSE_FINANCIALS[courseId]) {
    return RAW_COURSE_FINANCIALS[courseId];
  }

  const courseName = normalizeCourseKey((row as CourseLike).curso || (row as CourseLike).course);
  if (!courseName) return null;

  const exact = NAME_INDEX.find((item) => item.key === courseName);
  if (exact) return exact.entry;

  const partial = NAME_INDEX.find((item) => courseName.includes(item.key) || item.key.includes(courseName));
  return partial?.entry || null;
}

export function lookupCourseFinancial(course: CourseLike | string | null | undefined): CourseFinancialEntry | null {
  const legacy = lookupLegacyCourseFinancial(course);
  if (typeof course !== "object" || !course) return legacy;
  try {
    const unitValue = normalizeCourseUnitValue(course.valor_unitario);
    return unitValue == null ? legacy : { ...legacy, unitValue, source: "Cadastro da solução" };
  } catch {
    return null;
  }
}

export function formatCurrencyBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL"
  }).format(Number.isFinite(value) ? value : 0);
}

export function formatCompactCurrencyBRL(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    notation: "compact",
    maximumFractionDigits: 1
  }).format(Number.isFinite(value) ? value : 0);
}

export function courseFinancialLabel(course: CourseLike | string | null | undefined) {
  const financial = lookupCourseFinancial(course);
  return financial ? formatCurrencyBRL(financial.unitValue) : "Sem valor cadastrado";
}
