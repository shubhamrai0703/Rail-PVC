import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  CONTRACT_FIXTURES,
  grossOfferValue,
  netOfferValue,
  totalAdvertised,
} from "@/lib/wireframes/extraction";
import { Step1Upload } from "./Step1Upload";
import { Step2Pricing } from "./Step2Pricing";
import { Step3Items } from "./Step3Items";
import { Step4Bills } from "./Step4Bills";
import { Step5Reconcile } from "./Step5Reconcile";

const [twoSchedule, threeSchedule] = CONTRACT_FIXTURES;

const SCREENS: [string, string][] = [
  ["upload", renderToStaticMarkup(<Step1Upload />)],
  [
    "pricing",
    renderToStaticMarkup(
      <Step2Pricing contract={twoSchedule} onSelectContract={() => {}} />,
    ),
  ],
  ["items", renderToStaticMarkup(<Step3Items />)],
  ["bills", renderToStaticMarkup(<Step4Bills />)],
  ["reconcile", renderToStaticMarkup(<Step5Reconcile />)],
];

describe("extraction wireframe — invariants that must hold on every screen", () => {
  it.each(SCREENS)("%s screen offers a manual-entry escape hatch", (_name, markup) => {
    expect(markup).toMatch(/enter (this|bill|the contract)|by hand|Skip extraction|blank form/i);
  });

  it.each(SCREENS)("%s screen renders without throwing", (_name, markup) => {
    expect(markup.length).toBeGreaterThan(0);
  });
});

describe("pricing chain", () => {
  const markup = renderToStaticMarkup(
    <Step2Pricing contract={threeSchedule} onSelectContract={() => {}} />,
  );

  it("holds its arithmetic for a three-schedule contract with a non-zero rebate", () => {
    expect(threeSchedule.schedules).toHaveLength(3);
    expect(threeSchedule.overallRebatePct.value).toBe(2.75);

    // 8,100,000 + 3,200,000 + 4,080,000
    expect(grossOfferValue(threeSchedule)).toBe(15_380_000);
    // 18,000,000 + 4,000,000 + 6,000,000
    expect(totalAdvertised(threeSchedule)).toBe(28_000_000);
    // gross less 2.75% — the rebate applies here, to the gross total
    expect(netOfferValue(threeSchedule)).toBeCloseTo(14_957_050, 2);
  });

  it("keeps advertised and accepted visibly distinct", () => {
    expect(markup).toContain("Total advertised value");
    expect(markup).toContain("Accepted value");
    // The two must not resolve to the same number, or the screens have conflated them.
    expect(totalAdvertised(threeSchedule)).not.toBe(netOfferValue(threeSchedule));
  });

  it("states that the rebate applies to the gross total, never to item rates", () => {
    expect(markup).toContain("does not touch any");
    expect(markup).toMatch(/gross total of all schedules/i);
  });

  it("renders a rate-source combobox rather than a closed dropdown", () => {
    expect(markup).toContain('list="rate-source-suggestions"');
    // IRUSSOR is precisely the value no shipped enum contains.
    expect(markup).toContain("IRUSSOR");
  });

  it("marks the extra-items flag as affecting the calculation", () => {
    expect(markup).toContain("Contains extra items");
    expect(markup).toContain("Affects the calculation");
  });

  it("flags per-item escalation as an unmodelled schema decision", () => {
    expect(markup).toContain("Open schema decision");
  });

  it("surfaces a missing base month as blocked rather than defaulting it", () => {
    expect(threeSchedule.baseMonth.state).toBe("missing");
    expect(threeSchedule.baseMonth.value).toBeNull();
    expect(markup).toContain("blank, not zero");
    expect(markup).toContain("Not found in any uploaded document");
  });
});

describe("provenance", () => {
  it("shows a document and page for every proposed value on the pricing screen", () => {
    const markup = renderToStaticMarkup(
      <Step2Pricing contract={twoSchedule} onSelectContract={() => {}} />,
    );
    expect(markup).toContain("FIN-TAB tabulation statement.pdf");
    expect(markup).toContain("p.2");
    expect(markup).toContain("&#x27;Advt. Value (Rs.)&#x27; column");
  });

  it("offers both sides of a cross-document conflict", () => {
    const markup = renderToStaticMarkup(
      <Step2Pricing contract={twoSchedule} onSelectContract={() => {}} />,
    );
    expect(markup).toContain("Two documents disagree");
    expect(markup).toContain("Use this one");
    expect(markup).toContain("LOA.pdf");
  });
});

describe("manual entry at the point of rejection", () => {
  const markup = renderToStaticMarkup(
    <Step2Pricing contract={threeSchedule} onSelectContract={() => {}} />,
  );

  it("offers to type a value rather than only reject it", () => {
    expect(markup).toContain("Reject &amp; type");
  });

  it("opens an input straight away for a value that was never extracted", () => {
    // Base month is `missing` on this fixture, so the row must already be asking for it.
    expect(markup).toContain("Enter base month yourself");
    expect(markup).toContain("YYYY-MM, e.g. 2024-12");
  });

  it("offers fixed choices instead of free text where the field is a boolean", () => {
    expect(markup).toContain("Contains extra items");
    expect(markup).toContain("Yes — items need an eligibility decision");
  });

  it("lets the user reject both sides of a conflict and type their own value", () => {
    // The conflict lives on the two-schedule fixture, where alternatives exist —
    // so the row offers them first and keeps manual entry one click away.
    const conflictMarkup = renderToStaticMarkup(
      <Step2Pricing contract={twoSchedule} onSelectContract={() => {}} />,
    );
    expect(conflictMarkup).toContain("None of these are right — type the value myself");
  });

  it("labels the fixture switcher as wireframe scaffolding, not a real control", () => {
    expect(markup).toContain("Wireframe control — not part of the screen");
  });
});

describe("unhappy paths", () => {
  it("upload screen degrades for a scanned, text-layer-free document", () => {
    const markup = renderToStaticMarkup(<Step1Upload />);
    expect(markup).toContain("Scanned image");
    expect(markup).toContain("no text layer");
    expect(markup).toContain("Needs a type");
  });

  it("items screen blocks an unreadable classification instead of guessing", () => {
    const markup = renderToStaticMarkup(<Step3Items />);
    expect(markup).toContain("This item cannot be classified from the documents");
  });

  it("bill screen distinguishes the period end that drives the quarter", () => {
    const markup = renderToStaticMarkup(<Step4Bills />);
    expect(markup).toContain("Period end — selects the quarter");
    expect(markup).toContain("Period start — evidence only");
  });

  it("reconciliation refuses to write when checks fail or cannot run", () => {
    const markup = renderToStaticMarkup(<Step5Reconcile />);
    expect(markup).toContain("Nothing will be saved");
    expect(markup).toContain("Could not run.");
    expect(markup).toContain("disabled");
  });
});
