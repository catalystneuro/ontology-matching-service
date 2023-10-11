import React, { useState } from 'react';
import './App.css';
import { OntologyItem } from './types';
import OntologyBox from './OntologyBox';


const API_ENDPOINT = process.env.REACT_APP_API_ENDPOINT;
console.log("API Service Location:", API_ENDPOINT);  // Remove this line in production

function App() {

    const [text, setText] = useState('');
    const [data, setData] = useState<OntologyItem[]>([]);
    const [isLoading, setIsLoading] = useState(false);



    const handleSubmit = async () => {
        setIsLoading(true);
        setData([]); // Clear the previous results
        try {
            const response = await fetch(`${API_ENDPOINT}/get_ontology_matches/?text=${encodeURIComponent(text)}`);
            const result = await response.json();
            setData(result);
        } catch (error) {
            console.error('Error fetching data:', error);
        } finally {
            setIsLoading(false);
        }
    };

    return (
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
                    <button onClick={handleSubmit}>Submit</button>
                </div>
            </div>
            <div className="section-wrapper">
                <div className="white-box">
                    {isLoading ? 
                        <div className="loading-bar">Fetching matching ontology terms...</div>
                        :
                        (data.length === 0 ?
                            <div className="no-results">No results were found.</div>
                            :
                            data.map((item, index) => (
                                <OntologyBox key={index} item={item} />
                            ))
                        )
                    }
                </div>
            </div>
        </div>
    );
}

export default App;