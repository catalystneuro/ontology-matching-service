export type OntologyItem = {
    definition: string;
    id: string;
    name: string;
    parent_structure: OntologyItem[];
    synonyms?: string;
    text_to_embed?: string;
};