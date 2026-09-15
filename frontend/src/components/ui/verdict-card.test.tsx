import { render, screen } from "@testing-library/react";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import type { Verdict } from "@/api";
import { setLocalePreference } from "@/i18n";

import { VerdictCard } from "./verdict-card";

// The labels follow the language; happy-dom reports English, the assertions read French.
beforeAll(() => setLocalePreference("fr"));
afterAll(() => setLocalePreference("auto"));

const red: Verdict = {
  id: "fees",
  title: "Frais réels",
  status: "red",
  headline: "Tes placements te coûtent 2,00 % par an, soit 1 000 €.",
  impact_eur_per_year: 850,
  action: "Change de courtier.",
  details: {},
};

describe("VerdictCard", () => {
  it("shows the status, the sentence, the euros and the action without opening", () => {
    render(
      <VerdictCard verdict={red}>
        <p>détail du calcul</p>
      </VerdictCard>,
    );
    expect(screen.getByText("Frais réels")).toBeInTheDocument();
    expect(screen.getByText("À corriger")).toBeInTheDocument();
    expect(screen.getByText(/2,00 % par an/)).toBeInTheDocument();
    expect(screen.getByText(/850/)).toBeInTheDocument();
    expect(screen.getByText("Change de courtier.")).toBeInTheDocument();
    expect(screen.queryByText("détail du calcul")).not.toBeInTheDocument();
  });

  it("hides the amount when there is nothing to gain", () => {
    render(<VerdictCard verdict={{ ...red, status: "green", impact_eur_per_year: 0 }} />);
    expect(screen.getByText("Rien à changer")).toBeInTheDocument();
    expect(screen.queryByText(/\/an/)).not.toBeInTheDocument();
  });
});
