import React from 'react';
import { useParams } from 'react-router-dom';
import Agent from './AgentScreen.jsx';
import ErrorPage from './ErrorPage.jsx';

// Valid regions for the Agent UI
const VALID_REGIONS = ['us-west', 'us-central'];

export default function AgentRoute() {
    const params = useParams();
    const region = params.region;

    if (!region || !VALID_REGIONS.includes(region)) {

        const links = VALID_REGIONS.map(r => ({ to: `/agent/${r}`, label: r }));
        return (
            <ErrorPage
                title="Invalid Region"
                message={`The region '${region || ''}' is not valid for the agent view.`}
                links={links}
            />
        );
    }


    return <Agent />;
}
