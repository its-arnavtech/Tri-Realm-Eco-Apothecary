export type RealmSlug = "forest" | "ocean" | "mountain";

export type Realm = {
  slug: RealmSlug;
  number: string;
  name: string;
  tagline: string;
  introduction: string;
  perspective: string;
  color: string;
};

export type Concept = {
  slug: string;
  number: number;
  name: string;
  realm: RealmSlug | "tri-realm";
  format: string;
  summary: string;
  story: string;
  exploration: string[];
  questions: string[];
};

export const realms: Realm[] = [
  {
    slug: "forest",
    number: "01",
    name: "Forest",
    tagline: "Rooted in renewal",
    introduction: "A quieter perspective shaped by canopy, soil, and the patience of living systems.",
    perspective: "Forest guides our questions about ingredients, materials, and the care we bring into everyday spaces.",
    color: "#244835",
  },
  {
    slug: "ocean",
    number: "02",
    name: "Ocean",
    tagline: "Moved by tides",
    introduction: "An invitation to think about compact formats, movement, and the places our choices reach.",
    perspective: "Ocean inspires exploration. Any claim about water safety or biodegradability would need product-specific evidence.",
    color: "#1b5362",
  },
  {
    slug: "mountain",
    number: "03",
    name: "Mountain",
    tagline: "Made for clarity",
    introduction: "A sense of space and simplicity, drawn from stone, elevation, and the long view.",
    perspective: "Mountain brings a focus on clear information, useful design, and the details that deserve testing.",
    color: "#575d59",
  },
];

export const concepts: Concept[] = [
  {
    slug: "pine-mycelium-grounding-drops",
    number: 14,
    name: "Pine & Mycelium Grounding Drops",
    realm: "forest",
    format: "Concentrated drops concept",
    summary: "A forest-inspired thought experiment in concentrated care for the home.",
    story: "What might a smaller, more intentional home-care format feel like? Brew No. 14 begins with that question and a visual language drawn from the forest floor.",
    exploration: ["Concentrated format", "Ingredient selection", "Packaging direction"],
    questions: ["Final purpose and formulation", "Safety and surface compatibility", "Sourcing and packaging evidence"],
  },
  {
    slug: "tidal-dissolving-pods",
    number: 45,
    name: "Tidal Dissolving Pods",
    realm: "ocean",
    format: "Dissolving pod concept",
    summary: "A compact-format idea inspired by the rhythm and reach of water.",
    story: "Brew No. 45 explores how a compact format could change the experience of household care. The ocean is an inspiration for the design, never a substitute for evidence about aquatic impact.",
    exploration: ["Compact format", "Material choices", "Instructions and use"],
    questions: ["Final formulation and performance", "Aquatic safety testing", "Verified environmental claims"],
  },
  {
    slug: "glacial-mineral-elixir",
    number: 61,
    name: "Glacial Mineral Elixir",
    realm: "mountain",
    format: "Concentrate concept",
    summary: "A mountain-inspired study in simplicity, clarity, and considered materials.",
    story: "Brew No. 61 takes its visual cues from stone and elevation. Its purpose, formulation, and practical use remain open questions while the concept is explored.",
    exploration: ["Concentrate format", "Material palette", "Clear product information"],
    questions: ["Final use and compatibility", "Safety and stability testing", "Evidence for any performance claims"],
  },
  {
    slug: "tri-realm-catalyst",
    number: 67,
    name: "The Tri-Realm Catalyst",
    realm: "tri-realm",
    format: "Starter kit concept",
    summary: "A proposed starter format that brings the three realms into one story.",
    story: "The idea behind Brew No. 67 is a thoughtful household ritual inspired by Forest, Ocean, and Mountain. It is a design concept, with no approved formulation or use instructions.",
    exploration: ["Reusable vessel idea", "Tablet format", "A guided household ritual"],
    questions: ["Formulation and safety", "Use instructions and labeling", "Packaging and environmental evidence"],
  },
];

export const conceptBySlug = (slug: string) => concepts.find((concept) => concept.slug === slug);
export const realmBySlug = (slug: string) => realms.find((realm) => realm.slug === slug);
