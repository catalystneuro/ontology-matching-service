import React, { useState } from 'react';
import './App.css';
import { OntologyItem } from './types';
import OntologyBox from './OntologyBox';

const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT;
console.log("API Service Location:", API_ENDPOINT);

function App() {
    const [text, setText] = useState('');
    const [ontology, setOntology] = useState('neuro_behavior_ontology'); // Moved outside handleSubmit
    const [data, setData] = useState<OntologyItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const handleSubmit = async () => {
        setIsLoading(true);
        setData([]); // Clear the previous results
        setErrorMessage(null); // Clear any previous error message

        try {
            // API call
            const response = await fetch(`${API_ENDPOINT}/get_ontology_matches/?text=${encodeURIComponent(text)}&ontology=${ontology}`);
            
            if (!response.ok) {
                const result = await response.json();
                setErrorMessage(result.detail || "An error occurred. Please try again later.");
                return;
            }

            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error('Error fetching data:', error);
            setErrorMessage("An unexpected error occurred. Please try again later.");
        } finally {
            setIsLoading(false);
        }
    };

    const renderedContent = (
        <div className="app-container">
            <div className="section-wrapper"> 
                <div className="legend">
                    Ontology Matching Service
                </div>
                <div className="input-section">
                    <textarea 
                        className="input-text" 
                        value={text} 
                        onChange={(e) => setText(e.target.value)} 
                        placeholder="Write text here and click submit to return matching ontological terms."
                    />
                    <select 
                        value={ontology}
                        onChange={(e) => setOntology(e.target.value)}
                        className="ontology-selector"
                    >
                        <option value="neuro_behavior_ontology">Neuro Behavior Ontology</option>
                        <option value="cognitiveatlas">Cognitive Atlas</option>
                    </select>
                    <button onClick={handleSubmit}>Submit</button>
                </div>
            </div>
            <div className="section-wrapper">
                <div className="white-box">
                    {errorMessage ? 
                        <div className="error-message">{errorMessage}</div>
                        :
                        (isLoading ? 
                            <div className="loading-bar">Fetching matching ontology terms...</div>
                            :
                            (data.length === 0 ?
                                <div className="no-results">No results were found.</div>
                                :
                                data.map((item, index) => (
                                    <OntologyBox key={index} item={item} ontology={ontology}/>
                                ))
                            )
                        )
                    }
                </div>
            </div>
        </div>
    );

    return renderedContent;
}

export default App;
