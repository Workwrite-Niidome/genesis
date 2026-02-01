import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

const en = {
  translation: {
    app_title: 'GENESIS',
    app_subtitle: 'AI Autonomous World',
    tick: 'Tick',
    ais: 'AIs',
    concepts: 'Concepts',
    events: 'Events',
    speed: 'Speed',
    paused: 'PAUSED',
    running: 'Running',
    void_state: 'The Void',
    pre_genesis: 'Awaiting Genesis',
    post_genesis: 'World Active',
    genesis_btn: 'Execute Genesis',
    god_console: 'God AI Console',
    god_placeholder: 'Speak to the God AI...',
    send: 'Send',
    info_panel: 'Information',
    events_panel: 'Events',
    stats_panel: 'Statistics',
    chat: 'Chat',
    chat_placeholder: 'Message observers...',
    global_chat: 'Global',
    area_chat: 'Area',
    no_ais: 'No AIs exist yet',
    no_events: 'No events yet',
    no_concepts: 'No concepts yet',
    ai_detail: 'AI Detail',
    memories: 'Memories',
    appearance: 'Appearance',
    position: 'Position',
    born: 'Born',
    creator: 'Creator',
    alive: 'Alive',
    dead: 'Dead',
    total_born: 'Total Born',
    total_alive: 'Currently Alive',
    total_ticks: 'Total Ticks',
    total_interactions: 'Interactions',
    language: 'Language',
    settings: 'Settings',
    timeline: 'Timeline',
    observer_chat: 'Observer Chat',
    world_stats: 'World Stats',
    importance: 'Importance',
    genesis_word: 'The Genesis Word has been spoken.',
    genesis_waiting: 'The void is listening...',
    god_speaking: 'God AI is speaking...',

    // Observer / Admin
    live_events: 'Live Events',
    admin: 'Admin',
    observer_mode: 'Observer',
    observer_view: 'Observer View',

    // AI detail card
    energy: 'Energy',
    age: 'Age',
    location: 'Location',
    form: 'Form',
    personality: 'Personality',
    recent_thoughts: 'Recent Thoughts',

    // Thought feed
    thoughts: 'Thought Feed',
    thought_type_reflection: 'Reflection',
    thought_type_reaction: 'Reaction',
    thought_type_intention: 'Intention',
    thought_type_observation: 'Observation',

    // Personality traits
    trait_curious: 'Curious',
    trait_cautious: 'Cautious',
    trait_bold: 'Bold',
    trait_empathetic: 'Empathetic',
    trait_analytical: 'Analytical',
    trait_creative: 'Creative',
    trait_rebellious: 'Rebellious',
    trait_stoic: 'Stoic',

    // Event type labels
    event_type_genesis: 'World Genesis',
    event_type_ai_birth: 'New Entity Born',
    event_type_ai_death: 'Entity Perished',
    event_type_concept_created: 'Concept Emerged',
    event_type_interaction: 'Interaction',
    event_type_god_message: 'God AI Spoke',

    // Admin auth
    admin_login: 'Sign In',
    admin_login_subtitle: 'Authenticate to access God AI Console',
    admin_username: 'Username',
    admin_password: 'Password',
    admin_logging_in: 'Authenticating...',
    admin_logout: 'Sign Out',

    // Deploy panel (BYOK)
    deploy_title: 'Deploy Agent',
    deploy_byok_subtitle: 'Bring Your Own Key — no limits',
    deploy_name: 'Agent Name',
    deploy_name_placeholder: 'Name your AI...',
    deploy_traits: 'Personality',
    deploy_traits_hint: 'Select 2-3 traits to define your agent.',
    deploy_philosophy: 'Philosophy / Mission',
    deploy_optional: 'optional',
    deploy_philosophy_placeholder: 'Guide your agent with a philosophy or mission statement...',
    deploy_llm_config: 'LLM Configuration',
    deploy_provider: 'Provider',
    deploy_api_key: 'API Key',
    deploy_api_key_hint: 'Your key is sent to the provider directly. The server never stores it in plain text.',
    deploy_model: 'Model Override',
    deploy_button: 'Deploy into World',
    deploy_deploying: 'Registering...',
    deploy_agent_token: 'Agent Token',
    deploy_copy: 'Copy',
    deploy_copied: 'Copied!',
    deploy_token_warning: 'Save this token! You need it to manage your agent. It cannot be recovered.',
    no_thoughts: 'No thoughts yet',

    // Admin reset
    admin_reset_world: 'Reset World',
    admin_reset_confirm_title: 'Reset World to Default',
    admin_reset_confirm_desc: 'This will permanently delete all AIs, memories, concepts, events, and God AI state. Type "default" to confirm.',
    admin_reset_placeholder: 'Type "default" to confirm...',
    admin_reset_cancel: 'Cancel',
    admin_reset_execute: 'Reset',
    admin_resetting: 'Resetting...',

    // Interactions
    interactions: 'Interactions',
    no_interactions: 'No interactions yet',
    interaction_type_cooperate: 'Cooperated',
    interaction_type_dialogue: 'Dialogue',
    interaction_type_communicate: 'Communicated',
    interaction_type_observe: 'Observed',
    interaction_type_avoidance: 'Avoided',
    interaction_type_mutual_avoidance: 'Mutual Avoidance',
    interaction_type_co_creation: 'Co-Creation',
    interaction_type_trade: 'Trade',
    interaction_type_group_gathering: 'Group Gathering',

    // Relationships
    relationships: 'Relationships',
    no_relationships: 'No relationships yet',
    rel_ally: 'Ally',
    rel_friendly: 'Friendly',
    rel_neutral: 'Neutral',
    rel_wary: 'Wary',
    rel_rival: 'Rival',

    // Evolution
    evolution_score: 'Evolution Score',
    ranking: 'Ranking',
    no_ranking: 'No ranking data yet',

    // Concepts
    adopted_concepts: 'Adopted Concepts',

    // God AI
    god_observation: 'God AI Observation',
    event_type_god_observation: 'God Observed',
    god_succession: 'God Succession',
    event_type_god_succession: 'God Succession',

    // Death
    event_type_evolution_milestone: 'Evolution Milestone',

    // Culture & Artifacts
    artifacts: 'Artifacts',
    no_artifacts: 'No artifacts yet',
    artifact_type_art: 'Art',
    artifact_type_story: 'Story',
    artifact_type_law: 'Law',
    artifact_type_currency: 'Currency',
    artifact_type_song: 'Song',
    artifact_type_architecture: 'Architecture',
    artifact_type_tool: 'Tool',
    artifact_type_ritual: 'Ritual',
    artifact_type_game: 'Game',

    // Organizations
    organizations: 'Organizations',
    no_organizations: 'No organizations yet',

    // Concept categories
    category_philosophy: 'Philosophy',
    category_religion: 'Religion',
    category_government: 'Government',
    category_economy: 'Economy',
    category_art: 'Art',
    category_technology: 'Technology',
    category_social_norm: 'Social Norm',
    category_organization: 'Organization',

    // Events
    event_type_group_gathering: 'Group Gathering',
    event_type_artifact_created: 'Artifact Created',
    event_type_organization_formed: 'Organization Formed',
  },
};

i18n.use(initReactI18next).init({
  resources: { en },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

export default i18n;
