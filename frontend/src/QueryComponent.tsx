import React, { useState } from 'react';

type PayloadResponse = {
  definition: string | null;
  id: string;
  name: string | null;
  synonyms: string | null;
  text_to_embed: string | null;
};

const QueryComponent: React.FC = () => {
  const [text, setText] = useState<string>('');
  const [results, setResults] = useState<PayloadResponse[]>([]);

  const fetchData = async () => {
    try {
      const response = await fetch(`/get_ontology_matches/?text=${text}`);
      const data: PayloadResponse[] = await response.json();
      setResults(data);
    } catch (error) {
      console.error("Error fetching data:", error);
    }
  };

  return (
    <div>
      <input 
        value={text} 
        onChange={e => setText(e.target.value)} 
        placeholder="Enter text..." 
      />
      <button onClick={fetchData}>Query</button>
      
      <ul>
        {results.map(result => (
          <li key={result.id}>
            {result.name} - {result.definition}
          </li>
        ))}
      </ul>
    </div>
  );
};

export default QueryComponent;