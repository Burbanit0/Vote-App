// src/pages/SimulationPage.tsx

import React, { useState } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import SimulationForm, { SimulationFormData } from '../components/Simulation/SimulationForm';
import SimulationResult, { SimulationResponse } from '../components/Simulation/SimulationResult';
import { simulateVote } from '../services';
import { useTranslation } from 'react-i18next';
import VoterVisualization from '../components/Simulation/VoterVisualization';
import CandidatesVisualization from '../components/Simulation/CandidatesVisualization';
import UtilityVisualization from '../components/Simulation/UtilityVisualization';

const SimulateVotesPage: React.FC = () => {
  const { t } = useTranslation();
  const [result, setResult] = useState<SimulationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState<SimulationFormData>({
    simulationType: ['votes'],
    populationSize: 1000,
    candidates: ['Alice', 'Bob', 'Charlie'],
    turnoutRate: 0.7,
    demographics: {
      age: { '18-25': 0.2, '26-40': 0.3, '41-60': 0.3, '60+': 0.2 },
      gender: { male: 0.48, female: 0.48, 'non-binary': 0.04 },
      location: { urban: 0.5, suburban: 0.3, rural: 0.2 },
      education: { 'high-school': 0.3, bachelor: 0.4, advanced: 0.3 },
      income: { low: 0.2, middle: 0.6, high: 0.2 },
      ideology: { left: 0.35, center: 0.3, right: 0.35 },
    },
    influenceWeights: {
      location: {
        urban: { Alice: 1.5, Bob: 0.8, Charlie: 1.0 },
        suburban: { Alice: 1.0, Bob: 1.2, Charlie: 0.9 },
        rural: { Alice: 0.7, Bob: 1.3, Charlie: 1.1 },
      },
      income: {
        low: { Alice: 1.2, Bob: 0.9, Charlie: 1.0 },
        middle: { Alice: 1.0, Bob: 1.0, Charlie: 1.0 },
        high: { Alice: 0.8, Bob: 1.3, Charlie: 1.0 },
      },
      ideology: {
        left: { Alice: 2.0, Bob: 0.5, Charlie: 0.8 },
        center: { Alice: 1.0, Bob: 1.0, Charlie: 1.0 },
        right: { Alice: 0.5, Bob: 1.5, Charlie: 1.2 },
      },
    },
  });

  const simulateVotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await simulateVote(formData);
      setResult(response);
    } catch (error) {
      setError(t('simulation.errSimFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div data-style="tailwind" className="mx-auto w-full max-w-[1140px] px-3">
      <h2 className="my-6 text-2xl font-semibold">{t('simulation.pageTitleLegacy')}</h2>
      <Tabs defaultValue="Form" className="mb-4">
        <TabsList className="h-auto flex-wrap justify-start">
          <TabsTrigger value="Form">{t('simulation.tabForm')}</TabsTrigger>
          <TabsTrigger value="Voters">{t('simulation.tabVoters')}</TabsTrigger>
          <TabsTrigger value="Candidates">{t('simulation.tabCandidates')}</TabsTrigger>
          <TabsTrigger value="Utility">{t('simulation.tabUtility')}</TabsTrigger>
          <TabsTrigger value="Result">{t('simulation.tabResult')}</TabsTrigger>
        </TabsList>

        {/* forceMount keeps every panel in the DOM (like react-bootstrap's
            default), so deep-linked content + tests that read an inactive tab
            still work; radix hides the inactive ones. */}
        <TabsContent value="Form" forceMount>
          <SimulationForm
            simulateVotes={simulateVotes}
            loading={loading}
            formData={formData}
            setFormData={setFormData}
          />
          {error && (
            <div role="alert" className="mt-4 rounded-md border border-red-300 bg-red-100 px-3 py-2 text-sm text-red-800">
              {error}
            </div>
          )}
        </TabsContent>
        <TabsContent value="Voters" forceMount>
          <VoterVisualization />
        </TabsContent>
        <TabsContent value="Candidates" forceMount>
          <CandidatesVisualization />
        </TabsContent>
        <TabsContent value="Utility" forceMount>
          <UtilityVisualization />
        </TabsContent>
        <TabsContent value="Result" forceMount>
          <SimulationResult result={result} />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default SimulateVotesPage;
