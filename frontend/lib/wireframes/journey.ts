/**
 * Fixture data for the guided-journey wireframe.
 *
 * This exists because of one piece of user feedback, repeated by everyone who
 * has been shown the app: *"I don't understand where to start, or what to do
 * next."*
 *
 * The diagnosis behind this design:
 *
 * 1. There is no landing page. `NAV_ITEMS` goes straight to Contracts, Index
 *    Manager and Document Vault — three lists, no starting point.
 * 2. `JOURNEY_STAGES` renders a flat six-step ribbon, but it is decorative: the
 *    same six labels on every page regardless of what the contract has actually
 *    got. It says what the steps are, never which one you are on or which are
 *    done. It is also absent from `/contracts` and `/contracts/[id]` — the two
 *    pages people actually land on.
 * 3. The flat ribbon implies one linear pass. In reality setup happens **once**
 *    per contract and the bill cycle **repeats** for every MB. That is the part
 *    people get lost in: after their first bill they have no idea whether to go
 *    back to the start.
 *
 * So: two phases rather than one flat list, stage state derived from data, and
 * exactly one next action surfaced at a time.
 *
 * Stage order follows the reordered flow being implemented in parallel on
 * `saqlain/contract-flow-reorder` (contract → schedules → items → pricing
 * summary → bills), so the two do not diverge.
 */

export type StageState = "done" | "current" | "blocked" | "todo";

export type Stage = {
  id: string;
  label: string;
  /** What the user actually does here, in their words. */
  blurb: string;
  state: StageState;
  /** Why it is blocked. Required whenever state is `blocked`. */
  blockedReason?: string;
};

export type Phase = {
  id: string;
  title: string;
  /** The single most important thing about this phase. */
  cadence: string;
  stages: Stage[];
};

export type JourneyContract = {
  id: string;
  tenderNumber: string;
  contractorName: string;
  /** One sentence: what this contract needs from the user right now. */
  nextAction: string;
  nextActionLabel: string;
  /** Null when the contract is fully up to date. */
  blockedNote: string | null;
  phases: Phase[];
};

/** A contract mid-setup — the state most first-time users are in. */
const SETTING_UP: JourneyContract = {
  id: "ta-24-25-101",
  tenderNumber: "TA-24-25-101",
  contractorName: "Meridian Infra Pvt Ltd",
  nextAction:
    "Two schedules are saved but neither has any items yet. Add the BOQ items before raising a bill.",
  nextActionLabel: "Add items to Schedule A",
  blockedNote: null,
  phases: [
    {
      id: "setup",
      title: "Set up the contract",
      cadence: "Once — you will not come back here",
      stages: [
        {
          id: "contract",
          label: "Contract",
          blurb: "Tender number, contractor, base month and zone.",
          state: "done",
        },
        {
          id: "schedules",
          label: "Schedules",
          blurb: "One per rate book, each with its bid percentage.",
          state: "done",
        },
        {
          id: "items",
          label: "Items",
          blurb: "The BOQ, with cement and steel marked.",
          state: "current",
        },
        {
          id: "decisions",
          label: "Extra-item decisions",
          blurb: "Whether non-scheduled items are eligible for PVC.",
          state: "todo",
        },
        {
          id: "pricing",
          label: "Pricing check",
          blurb: "Confirm advertised and accepted values agree with the tabulation statement.",
          state: "todo",
        },
      ],
    },
    {
      id: "billing",
      title: "Bill and calculate",
      cadence: "Repeats — once for every measurement book",
      stages: [
        {
          id: "bill",
          label: "Bill",
          blurb: "Enter the MB quantities and the gross value.",
          state: "todo",
        },
        {
          id: "calculate",
          label: "Calculate",
          blurb: "Run PVC for the bill's quarter.",
          state: "todo",
        },
        {
          id: "review",
          label: "Review and approve",
          blurb: "Check the derivation, then approve and export.",
          state: "todo",
        },
      ],
    },
  ],
};

/** A contract blocked on something the user cannot guess at. */
const BLOCKED: JourneyContract = {
  id: "ta-24-25-207",
  tenderNumber: "TA-24-25-207",
  contractorName: "Northgate Constructions",
  nextAction:
    "Bill 2 covers May 2025, but the WPI steel index for May 2025 has not been entered yet. The calculation cannot run without it.",
  nextActionLabel: "Add May 2025 steel index",
  blockedNote:
    "This is the single most common dead end: a bill is ready but its quarter has no index data. Nothing on the bill page explains it today.",
  phases: [
    {
      id: "setup",
      title: "Set up the contract",
      cadence: "Once — you will not come back here",
      stages: [
        { id: "contract", label: "Contract", blurb: "Tender number, contractor, base month and zone.", state: "done" },
        { id: "schedules", label: "Schedules", blurb: "One per rate book, each with its bid percentage.", state: "done" },
        { id: "items", label: "Items", blurb: "The BOQ, with cement and steel marked.", state: "done" },
        { id: "decisions", label: "Extra-item decisions", blurb: "Whether non-scheduled items are eligible for PVC.", state: "done" },
        { id: "pricing", label: "Pricing check", blurb: "Confirm advertised and accepted values agree with the tabulation statement.", state: "done" },
      ],
    },
    {
      id: "billing",
      title: "Bill and calculate",
      cadence: "Repeats — once for every measurement book",
      stages: [
        { id: "bill", label: "Bill", blurb: "Enter the MB quantities and the gross value.", state: "done" },
        {
          id: "calculate",
          label: "Calculate",
          blurb: "Run PVC for the bill's quarter.",
          state: "blocked",
          blockedReason:
            "No steel index for May 2025. Quarter 3 needs March, April and May before it can average.",
        },
        { id: "review", label: "Review and approve", blurb: "Check the derivation, then approve and export.", state: "todo" },
      ],
    },
  ],
};

/** A contract in steady state — the repeat cadence made visible. */
const STEADY: JourneyContract = {
  id: "ta-23-24-088",
  tenderNumber: "TA-23-24-088",
  contractorName: "Ashwin Engineering Works",
  nextAction:
    "Bills 1 to 3 are approved. Start bill 4 when the next measurement book is signed.",
  nextActionLabel: "Start bill 4",
  blockedNote: null,
  phases: [
    {
      id: "setup",
      title: "Set up the contract",
      cadence: "Once — you will not come back here",
      stages: [
        { id: "contract", label: "Contract", blurb: "Tender number, contractor, base month and zone.", state: "done" },
        { id: "schedules", label: "Schedules", blurb: "One per rate book, each with its bid percentage.", state: "done" },
        { id: "items", label: "Items", blurb: "The BOQ, with cement and steel marked.", state: "done" },
        { id: "decisions", label: "Extra-item decisions", blurb: "Whether non-scheduled items are eligible for PVC.", state: "done" },
        { id: "pricing", label: "Pricing check", blurb: "Confirm advertised and accepted values agree with the tabulation statement.", state: "done" },
      ],
    },
    {
      id: "billing",
      title: "Bill and calculate",
      cadence: "Repeats — 3 bills approved so far",
      stages: [
        { id: "bill", label: "Bill", blurb: "Enter the MB quantities and the gross value.", state: "current" },
        { id: "calculate", label: "Calculate", blurb: "Run PVC for the bill's quarter.", state: "todo" },
        { id: "review", label: "Review and approve", blurb: "Check the derivation, then approve and export.", state: "todo" },
      ],
    },
  ],
};

export const JOURNEY_CONTRACTS: readonly JourneyContract[] = [
  SETTING_UP,
  BLOCKED,
  STEADY,
];

/** Shown to a tenant with nothing in it yet — the true "where do I start". */
export const FIRST_RUN_STEPS: readonly { label: string; blurb: string }[] = [
  {
    label: "Add your contract",
    blurb:
      "Start with the LOA or tender number. Everything else can follow later — you do not need the full agreement to begin.",
  },
  {
    label: "Enter the index data your quarters need",
    blurb:
      "PVC compares each bill's quarter against the base month. Without index observations for those months, nothing can be calculated.",
  },
  {
    label: "Raise your first bill",
    blurb:
      "One bill per measurement book. Setup does not repeat — from here on you only ever do this part.",
  },
];
