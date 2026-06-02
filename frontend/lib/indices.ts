// Series names are stored snake_case (e.g. "steel_tmt", "plant_machinery").
// A few have canonical display forms; the rest fall back to Title Case.
const SERIES_LABELS: Record<string, string> = {
  steel_tmt: "Steel — TMT bars",
  steel_angles: "Steel — Angles",
  steel_plates: "Steel — Plates",
  steel_other_sections: "Steel — Other sections",
  plant_machinery: "Plant & machinery",
  other_materials: "Other materials",
};

export function humanizeSeries(name: string): string {
  if (name in SERIES_LABELS) return SERIES_LABELS[name];
  return name
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
