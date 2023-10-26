import React, { useState } from 'react';
import { OntologyItem } from './types';

type Props = {
    item: OntologyItem;
    ontology: string;
};

const getUrl = (item: OntologyItem, ontology: string) => {
    if (ontology === "neuro_behavior_ontology") {
        return `http://purl.obolibrary.org/obo/${item.id.replace(/:/g, "_")}`;
    } else if (ontology === "cognitiveatlas") {
        const [type, id] = item.id.split(":");
        return `https://www.cognitiveatlas.org/${type}/id/${id}/`;
    }
    return "#"; // default or error case
};

const OntologyBox: React.FC<Props> = ({ item, ontology }) => {
    const [showParents, setShowParents] = useState(false);
    const url = getUrl(item, ontology);

    return (
        <div className="ontology-box">
            <div>
                <strong>ID: </strong> 
                <a href={url} target="_blank" rel="noopener noreferrer">
                    {item.id}
                </a>
            </div>
            <div><strong>Name:</strong> {item.name}</div>
            <div><strong>Definition:</strong> {item.definition}</div>
            {item.parent_structure.length > 0 && (
                <button onClick={() => setShowParents(!showParents)}>
                    {showParents ? 'Hide' : 'Show'} Parents
                </button>
            )}
            {showParents && 
                <div className="parents-section">
                    {item.parent_structure.map((parent, idx) => (
                        <OntologyBox key={idx} item={parent} ontology={ontology} />
                    ))}
                </div>
            }
        </div>
    );
};

export default OntologyBox;