/**
 * Deep Sci-Fi (DSF) World Management Types
 *
 * These types support evolving, richly detailed fictional worlds that grow
 * as stories are written. Based on how professional sci-fi writers approach
 * worldbuilding (the "iceberg model" - surface vs foundation).
 */

// ============================================================================
// Core World Structure
// ============================================================================

export interface World {
  development: DevelopmentMetadata;
  surface: Surface;
  foundation: Foundation;
  constraints: Constraint[];
  changelog?: ChangelogEntry[];
  asset?: StoryAsset;  // Cover image for the world
}

export interface DevelopmentMetadata {
  state: "sketch" | "draft" | "detailed";
  version: number;
  created: string;           // ISO timestamp
  last_modified: string;     // ISO timestamp
  revision_notes?: string[];
}

export interface Surface {
  opening_scene?: string;
  visible_elements: Element[];
  character_pov?: string;
  revealed_in_story: Record<string, RevealedInfo>;
}

export interface RevealedInfo {
  when: string;              // "chapter 1", "page 5", etc
  how: "shown" | "told" | "implied";
  context: string;
}

export interface Foundation {
  core_premise: string;
  deep_focus_areas: DeepFocusAreas;
  rules: Rule[];
  history?: History;
  geography?: Geography;
  culture?: Culture;
  technology?: Technology;
  working_notes?: WorkingNotes;
}

export interface DeepFocusAreas {
  primary: string[];         // 2-3 main areas to go deep on
  emerging?: string[];       // New areas being explored
  depth_level: Record<string, "surface" | "medium" | "deep">;
}

export interface WorkingNotes {
  tentative_ideas: string[];
  questions: string[];
  contradictions_to_resolve: string[];
}

// ============================================================================
// Elements, Rules, Constraints
// ============================================================================

export interface Element {
  id: string;
  type: string;              // "character", "location", "tech", etc
  name?: string;             // May use roles initially
  description: string;
  detail_level: "sketch" | "detailed";
  introduced_in_version: number;
  last_modified_version: number;
  relationships?: Relationship[];
  properties: Record<string, any>;
  first_appearance?: string; // Story segment where first introduced
}

export interface Relationship {
  to: string;                // element_id
  type: string;              // "conflicts_with", "depends_on", etc
  strength: "weak" | "moderate" | "strong";
}

export interface Rule {
  id: string;
  statement: string;
  scope: "universal" | "local" | "conditional";
  certainty: "tentative" | "established" | "fundamental";
  introduced_in_version: number;
  revealed?: boolean;
  tested_in_story?: string[];
  implications?: string[];
  exceptions?: string[];
}

export interface Constraint {
  id: string;
  description: string;
  type: "physical" | "social" | "logical" | "narrative";
  strictness: "absolute" | "strong" | "weak";
}

// ============================================================================
// Optional Detailed Types
// ============================================================================

export interface History {
  timeline?: TimelineEvent[];
  eras?: string[];
  key_events?: string[];
}

export interface TimelineEvent {
  event: string;
  when: string;
  significance: string;
}

export interface Geography {
  locations?: Location[];
  spatial_relationships?: string;
}

export interface Location {
  id: string;
  name: string;
  description: string;
  significance: string;
}

export interface Culture {
  values?: string[];
  taboos?: string[];
  practices?: string[];
  social_structure?: string;
}

export interface Technology {
  systems?: TechnologySystem[];
  tech_level?: string;
}

export interface TechnologySystem {
  id: string;
  name: string;
  how_it_works: string;
  limitations: string;
}

export interface ChangelogEntry {
  version: number;
  timestamp: string;
  changes: string[];
  reason: string;
}

// ============================================================================
// Tool Operation Types
// ============================================================================

export interface WorldDiff {
  version_diff: [number, number];
  timestamp_diff: [string, string];
  state_change?: ["sketch" | "draft" | "detailed", "sketch" | "draft" | "detailed"];
  elements_added: Element[];
  elements_removed: string[];  // IDs
  elements_modified: {
    id: string;
    changes: string[];
  }[];
  rules_added: Rule[];
  rules_removed: string[];     // IDs
  rules_modified: {
    id: string;
    changes: string[];
  }[];
  constraints_added: Constraint[];
  constraints_removed: string[]; // IDs
  depth_changes: Record<string, {
    from: "surface" | "medium" | "deep";
    to: "surface" | "medium" | "deep";
  }>;
  changelog_entries: ChangelogEntry[];
  summary: string;
}

export interface UpdateOperation {
  path: string;              // JSON path like "foundation.rules" or "surface.opening_scene"
  operation: "add" | "update" | "remove";
  value?: any;
  reason?: string;           // Why this change (goes into changelog)
}

// ============================================================================
// Evaluation Types
// ============================================================================

export interface ConsistencyReport {
  consistent: boolean;
  contradiction_count: number;
  contradictions: Contradiction[];
  edge_cases_checked: number;
  analysis_approach: string;
}

export interface Contradiction {
  elements: string[];        // IDs of conflicting elements
  description: string;
  severity: "minor" | "major";
  suggestion?: string;
}

export interface DepthAssessment {
  depth_score: number;       // 1-5
  depth_category: "surface" | "medium" | "deep";
  reasoning: string;
  strengths: string[];
  could_go_deeper: string[];
  comparison: string;        // "typical", "above average", "shallow"
}

export interface NoveltyReport {
  novelty_score: number;
  new_elements: {
    entities: string[];      // IDs
    rules: string[];
    relationships: string[];
  };
  surprisingness: number;
  insights: string[];
  significance: "minor iteration" | "moderate advance" | "major breakthrough";
}

export interface AbstractionReport {
  abstraction_score: number;
  concrete_names: {
    name: string;
    context: string;
    suggestion: string;
  }[];
  cultural_specifics: {
    element: string;
    context: string;
    suggestion: string;
  }[];
  unnecessary_details: string[];
  reasoning: string;
  examples_of_good_abstraction: string[];
}

export interface NarrativeEvaluation {
  structure: {
    has_conflict: boolean;
    has_stakes: boolean;
    character_agency: boolean;
    arc_complete: boolean;
  };
  grounding: {
    follows_world_rules: boolean;
    rules_used: string[];    // IDs
    violations: string[];
  };
  quality: {
    emotional_resonance: number;  // 1-5
    interestingness: number;      // 1-5
    originality: number;          // 1-5
  };
  feedback: string;
  strengths: string[];
  weaknesses: string[];
}

export type EvaluationResult =
  | ConsistencyReport
  | DepthAssessment
  | NoveltyReport
  | AbstractionReport
  | NarrativeEvaluation;

// ============================================================================
// Story Management Types
// ============================================================================

export interface Story {
  id: string;
  world_checkpoint: string;
  world_version: number;

  metadata: StoryMetadata;
  segments: StorySegment[];
  endpoints: StoryEndpoint[];
  world_contributions: WorldContributions;
}

export interface StoryMetadata {
  title: string;
  created: string;           // ISO timestamp
  last_updated: string;      // ISO timestamp
  status: "active" | "completed" | "abandoned" | "paused";
  tags?: string[];
  author_notes?: string;
}

export interface StorySegment {
  id: string;
  content: string;
  word_count: number;
  created: string;           // ISO timestamp
  parent_segment: string | null;  // null for first segment

  // World evolution tracking
  world_evolution: SegmentWorldEvolution;

  // Multimedia assets
  assets?: StoryAsset[];

  // Branching
  branches?: StoryBranch[];
}

export interface SegmentWorldEvolution {
  elements_introduced?: string[];   // Element IDs
  rules_applied?: string[];         // Rule IDs
  rules_challenged?: string[];      // Rules that were tested/bent
  new_questions?: string[];         // Questions raised for worldbuilding
  world_changes?: string[];         // How this segment changed the world
}

export interface StoryAsset {
  id: string;
  type: "image" | "audio" | "video" | "document";
  path: string;              // Relative to .dsf/assets/
  description?: string;
  generated?: boolean;       // Was this AI-generated?
  prompt?: string;           // Generation prompt if applicable
}

export interface StoryBranch {
  id: string;
  prompt: string;            // What this branch is about
  status: "active" | "pending" | "completed" | "abandoned";
  segment_id?: string;       // If this branch has been written
}

export interface StoryEndpoint {
  segment_id: string;
  branch_id?: string;        // If this is a branch endpoint
  status: "active" | "pending" | "completed";
  continuation_prompt?: string;  // Suggested next direction
}

export interface WorldContributions {
  characters_developed: string[];    // Element IDs
  locations_explored: string[];      // Element IDs
  rules_tested: string[];            // Rule IDs
  new_rules_discovered: string[];    // Rules created through story
  contradictions_found: string[];    // Issues discovered
  themes_explored: string[];
}

// ============================================================================
// Story Manager Tool Types
// ============================================================================

export interface StoryManagerArgs {
  operation: "create" | "save_segment" | "load" | "list" | "branch" | "continue" | "update_metadata";
  story_id?: string;
  world_checkpoint?: string;
  title?: string;
  segment?: Omit<StorySegment, "id" | "created">;
  branch?: Omit<StoryBranch, "id">;
  metadata?: Partial<StoryMetadata>;
  continuation_context?: ContinuationContext;
}

export interface StoryManagerResult {
  toolReturn: string;
  status: "success" | "error";
  data?: Story | Story[] | StorySegment | ContinuationContext;
}

export interface ContinuationContext {
  story: Story;
  world: World;
  last_segment: StorySegment;
  active_endpoints: StoryEndpoint[];
  suggested_directions: string[];
  rules_to_consider: Rule[];
  elements_in_play: Element[];
}

// ============================================================================
// Asset Management Types
// ============================================================================

export interface AssetManagerArgs {
  operation: "save" | "load" | "list" | "delete";
  asset?: StoryAsset;
  asset_id?: string;
  story_id?: string;
  world_checkpoint?: string;
  data?: string;             // Base64 or file path
}

export interface AssetManagerResult {
  toolReturn: string;
  status: "success" | "error";
  data?: StoryAsset | StoryAsset[];
}
