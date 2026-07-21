import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import {
  ExcelFieldGuide,
  JourneyGuide,
  NumberedStageGuide,
  PageGuidance,
  SupplementaryHelp,
} from "./FirstUserHelp";

describe("FirstUserHelp", () => {
  it("renders the full journey in order and marks the current stage", () => {
    const markup = renderToStaticMarkup(<JourneyGuide stage="decisions" />);

    expect(markup).toContain('aria-label="Contract to PVC journey"');
    expect(markup).toContain('aria-current="step"');
    expect(markup).not.toContain("truncate");
    expect(markup).toContain("whitespace-normal");
    expect(markup).toMatch(/Contract.*Items.*NS decisions.*Bill.*Calculate.*Review/);
  });

  it("renders reusable numbered stages with their supplied accessible label", () => {
    const markup = renderToStaticMarkup(
      <NumberedStageGuide
        ariaLabel="Import stages"
        currentId="map"
        items={[
          { id: "source", label: "Choose source" },
          { id: "map", label: "Map columns" },
        ]}
      />,
    );

    expect(markup).toContain('aria-label="Import stages"');
    expect(markup).toMatch(/>1<.*Choose source.*aria-current="step".*>2<.*Map columns/);
  });

  it("renders next-step guidance only when supplied", () => {
    const withNext = renderToStaticMarkup(
      <PageGuidance title="Create the bill" next="Calculate PVC.">
        Add the bill header.
      </PageGuidance>,
    );
    const withoutNext = renderToStaticMarkup(
      <PageGuidance title="Review the result">Check every value.</PageGuidance>,
    );

    expect(withNext).toContain('aria-label="Create the bill guidance"');
    expect(withNext).toContain("Next:");
    expect(withNext).toContain("Calculate PVC.");
    expect(withoutNext).not.toContain("Next:");
  });

  it("uses native disclosure semantics for supplementary help", () => {
    const markup = renderToStaticMarkup(
      <SupplementaryHelp summary="How this is used">
        Supporting explanation.
      </SupplementaryHelp>,
    );

    expect(markup).toContain("<details");
    expect(markup).toContain("<summary");
    expect(markup).toContain("How this is used");
    expect(markup).toContain("Supporting explanation.");
  });

  it("renders the Excel-to-TenderAudit field vocabulary", () => {
    const markup = renderToStaticMarkup(<ExcelFieldGuide />);

    expect(markup).toContain("Original quantity");
    expect(markup).toContain("Agreement Qty");
    expect(markup).toContain("Base rate");
    expect(markup).toContain("Agreement rate");
    expect(markup).toContain("Cement and steel subtype");
  });
});
