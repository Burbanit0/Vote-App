/**
 * ApportionmentPanel — demonstrates Balinski-Young impossibility theorem (1982):
 * no apportionment method can simultaneously satisfy quota rule, house monotonicity
 * (no Alabama paradox) and population monotonicity.
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Range } from '@/components/ui/form-controls';
import { Col, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { $api } from '../../api/hooks';

const METHODS = ['hamilton', 'jefferson', 'webster', 'adams', 'huntington_hill'] as const;

const COUNTRY_DATA = [
  { country: '🇺🇸 USA', method: 'Huntington-Hill', note: 'Paradoxe Alabama possible' },
  { country: '🇪🇺 UE', method: "D'Hondt (Jefferson)", note: 'Avantage grands partis' },
  { country: '🇩🇪 DE', method: 'Sainte-Laguë (Webster)', note: 'Le plus neutre connu' },
  { country: '🇫🇷 FR', method: 'Prime majoritaire', note: 'Pas vraiment proportionnel' },
  { country: '🇨🇭 CH', method: "D'Hondt modifié", note: 'Seuil électoral 5%' },
];

interface MethodResult {
  seats: Record<string, number>;
  quota_violation: boolean;
  alabama_paradox: boolean;
  population_paradox: boolean;
  new_state_paradox: boolean;
  favors: string;
  description: string;
}

interface ApportData {
  results: Record<string, MethodResult>;
  balinski_young_summary: string;
  impossible_to_avoid: string[];
  pedagogical_note: string;
}

// ── Method properties table ───────────────────────────────────────────────────

const METHOD_AXIOMS: Record<string, { quota: boolean; alabama: boolean; population: boolean }> = {
  hamilton: { quota: true, alabama: false, population: false },
  jefferson: { quota: false, alabama: true, population: true },
  webster: { quota: false, alabama: true, population: true },
  adams: { quota: false, alabama: true, population: true },
  huntington_hill: { quota: false, alabama: true, population: true },
};

// ── Main panel ────────────────────────────────────────────────────────────────

const ApportionmentPanel: React.FC = () => {
  const { t } = useTranslation();

  const [numSeats, setNumSeats] = useState(10);
  const sim = $api.useMutation('post', '/api/v2/theory/apportionment');
  const data: ApportData | null = (sim.data as ApportData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('appor.error') : null;
  const [sliderN, setSliderN] = useState(10);

  // Default parties (classic Alabama paradox example)
  const defaultParties = [
    { name: 'A', votes: 9000 },
    { name: 'B', votes: 7000 },
    { name: 'C', votes: 5000 },
  ];

  const runSimulation = useCallback(
    (n: number) => {
      sim.mutate({
        body: {
          parties: defaultParties,
          num_seats: n,
          methods: ['hamilton', 'jefferson', 'webster', 'adams', 'huntington_hill'],
          find_paradoxes: true,
        },
      });
    },
    [t, sim]
  );

  const handleSimulate = () => {
    setSliderN(numSeats);
    runSimulation(numSeats);
  };
  const handleSlider = (n: number) => {
    setSliderN(n);
    runSimulation(n);
  };

  const parties = Object.keys(data?.results?.hamilton?.seats ?? { A: 0, B: 0, C: 0 });

  return (
    <div>
      {/* Controls */}
      <Row className="g-2 mb-3 items-end">
        <Col xs={12} md={4}>
          <label className="mb-1 inline-block text-sm mb-0">
            {t('appor.numSeats')}: <strong>{numSeats}</strong>
          </label>
          <Range
            min={5}
            max={50}
            step={1}
            value={numSeats}
            data-testid="seats-slider"
            onChange={(e) => setNumSeats(Number(e.target.value))}
          />
        </Col>
        <Col xs="auto">
          <Button
            variant="primary"
            onClick={handleSimulate}
            disabled={loading}
            data-testid="simulate-btn"
          >
            {loading ? <Spinner size="sm" /> : t('appor.run')}
          </Button>
        </Col>
      </Row>

      {!data && !loading && !error && (
        <Alert variant="info" role="alert">
          {t('appor.prompt')}
        </Alert>
      )}
      {error && <Alert variant="danger">{error}</Alert>}

      {data && (
        <>
          {/* Method comparison table */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('appor.comparisonTitle')}
          </div>
          <div className="table-responsive mb-3" data-testid="comparison-table">
            <Table
              className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_th]:border [&_td]:border [&_tbody_tr:hover]:bg-muted/50"
              style={{ fontSize: '0.78rem' }}
            >
              <thead className="table-light">
                <tr>
                  <th>{t('appor.party')}</th>
                  {METHODS.filter((m) => data.results[m]).map((m) => (
                    <th key={m} style={{ textAlign: 'center' }}>
                      {m.replace('_', '-')}
                      {data.results[m]?.quota_violation && (
                        <Badge variant="danger" style={{ fontSize: '0.55rem', display: 'block' }}>
                          quota ✗
                        </Badge>
                      )}
                      {data.results[m]?.alabama_paradox && (
                        <Badge variant="warning" style={{ fontSize: '0.55rem', display: 'block' }}>
                          Alabama
                        </Badge>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parties.map((party) => (
                  <tr key={party}>
                    <td>
                      <strong>{party}</strong>
                    </td>
                    {METHODS.filter((m) => data.results[m]).map((m) => (
                      <td key={m} style={{ textAlign: 'center' }}>
                        {data.results[m].seats[party] ?? 0}
                      </td>
                    ))}
                  </tr>
                ))}
                {/* Total */}
                <tr className="table-light">
                  <td>
                    <strong>Total</strong>
                  </td>
                  {METHODS.filter((m) => data.results[m]).map((m) => (
                    <td key={m} style={{ textAlign: 'center', fontWeight: 700 }}>
                      {Object.values(data.results[m].seats).reduce((a, b) => a + b, 0)}
                    </td>
                  ))}
                </tr>
              </tbody>
            </Table>
          </div>

          {/* Alabama paradox slider demo */}
          <div className="mb-3" data-testid="alabama-demo">
            <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
              🎚 {t('appor.alabamaDemo')}
            </div>
            <div className="flex items-center gap-3">
              <Range
                min={5}
                max={30}
                step={1}
                value={sliderN}
                style={{ maxWidth: 200 }}
                data-testid="alabama-slider"
                onChange={(e) => handleSlider(Number(e.target.value))}
              />
              <span style={{ fontSize: '0.8rem' }}>
                {sliderN} {t('appor.seats')}
              </span>
            </div>
            {data.results.hamilton?.alabama_paradox && (
              <Alert
                variant="danger"
                className="mt-1 py-1"
                style={{ fontSize: '0.78rem' }}
                data-testid="alabama-alert"
              >
                ⚡ {t('appor.alabamaDetected', { n: sliderN })}
              </Alert>
            )}
          </div>

          {/* Method axioms table */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('appor.axiomsTitle')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50"
            data-testid="axioms-table"
            style={{ fontSize: '0.78rem' }}
          >
            <thead>
              <tr>
                <th>{t('appor.method')}</th>
                <th style={{ textAlign: 'center' }}>{t('appor.axQuota')}</th>
                <th style={{ textAlign: 'center' }}>{t('appor.axAlabama')}</th>
                <th style={{ textAlign: 'center' }}>{t('appor.axPopulation')}</th>
                <th>{t('appor.favors')}</th>
              </tr>
            </thead>
            <tbody>
              {METHODS.map((m) => {
                const ax = METHOD_AXIOMS[m];
                const res = data.results[m];
                if (!res) return null;
                return (
                  <tr key={m}>
                    <td>
                      <code>{m.replace('_', '-')}</code>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span style={{ color: ax.quota ? '#198754' : '#dc3545' }}>
                        {ax.quota ? '✓' : '✗'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span style={{ color: ax.alabama ? '#198754' : '#dc3545' }}>
                        {ax.alabama ? '✓' : '✗'}
                      </span>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <span style={{ color: ax.population ? '#198754' : '#dc3545' }}>
                        {ax.population ? '✓' : '✗'}
                      </span>
                    </td>
                    <td>
                      <Badge
                        variant={
                          res.favors === 'large_parties'
                            ? 'danger'
                            : res.favors === 'small_parties'
                              ? 'info'
                              : 'secondary'
                        }
                        style={{ fontSize: '0.6rem' }}
                      >
                        {t(`appor.favors_${res.favors}`)}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          {/* Balinski-Young impossibility */}
          <Alert variant="danger" style={{ fontSize: '0.8rem' }} data-testid="impossibility-alert">
            <strong>🔒 {t('appor.impossibilityTitle')}</strong> {data.balinski_young_summary}
          </Alert>

          {/* Country comparison */}
          <div className="font-semibold mb-1" style={{ fontSize: '0.85rem' }}>
            {t('appor.countryTitle')}
          </div>
          <Table
            className="[&_th]:p-1 [&_td]:p-1 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50"
            data-testid="country-table"
            style={{ fontSize: '0.78rem' }}
          >
            <thead>
              <tr>
                <th>{t('appor.country')}</th>
                <th>{t('appor.methodUsed')}</th>
                <th>{t('appor.note')}</th>
              </tr>
            </thead>
            <tbody>
              {COUNTRY_DATA.map((row) => (
                <tr key={row.country}>
                  <td>{row.country}</td>
                  <td>
                    <code>{row.method}</code>
                  </td>
                  <td className="text-muted-foreground">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </Table>

          {/* Pedagogical note */}
          <Alert variant="secondary" style={{ fontSize: '0.8rem' }}>
            <strong>{t('appor.noteTitle')}</strong> {data.pedagogical_note}
          </Alert>
        </>
      )}
    </div>
  );
};

export default ApportionmentPanel;
