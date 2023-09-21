import React, { useState } from 'react';
import { OntologyItem } from './types';

type Props = {
    item: OntologyItem;
};

const OntologyBox: React.FC<Props> = ({ item }) => {
    const [showParents, setShowParents] = useState(false);

    return (
        <div className="ontology-box">
            <div><strong>ID:</strong> {item.id}</div>
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
                        <OntologyBox key={idx} item={parent} />
                    ))}
                </div>
            }
        </div>
    );
};

export default OntologyBox;