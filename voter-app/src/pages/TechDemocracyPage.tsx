/**
 * TechDemocracyPage — pedagogical page on technological solutions for democracy.
 * Four sections:
 *   1. Why e-voting is hard
 *   2. E2E-V interactive demo (ElectionGuard / Helios / Belenios)
 *   3. Blockchain governance comparison table
 *   4. Pol.is consensus clustering demo
 */
import React, { useCallback, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardBody, CardHeader } from '@/components/ui/card';
import { Control, Select } from '@/components/ui/form-controls';
import { Col, Container, Row } from '@/components/ui/grid';
import { Spinner } from '@/components/ui/spinner';
import { Table } from '@/components/ui/table';
import { useMetaTags } from '../hooks/useMetaTags';
import PoliticalClusterMap, { PolisData } from '../components/shared/PoliticalClusterMap';
import E2EVDemo from '../components/shared/E2EVDemo';
import PolisPanel from '../components/shared/PolisPanel';
import { ElectionProvider } from '../stores/useElectionStore';
import { $api } from '../api/hooks';

// ── Types ─────────────────────────────────────────────────────────────────────

interface EncryptedBallot {
  voter_id: number;
  encrypted: string;
  code: string;
}

interface E2EData {
  num_voters: number;
  candidates: string[];
  encrypted_ballots: EncryptedBallot[];
  aggregate_result: Record<string, number>;
  verification_demonstration: {
    sample_voter_id: number;
    sample_code: string;
    board_excerpt: string[];
  };
  privacy_guarantee: string;
}

// ── Section 1 — E-voting incidents ────────────────────────────────────────────

const INCIDENTS = [
  {
    year: 2006,
    event: 'Diebold AccuVote — code source divulgué, vulnérabilités critiques',
    country: '🇺🇸',
  },
  {
    year: 2007,
    event: 'Pays-Bas : machines Nedap retirées après démonstration de piratage',
    country: '🇳🇱',
  },
  {
    year: 2009,
    event: 'Allemagne : Cour Constitutionnelle interdit le vote électronique opaque',
    country: '🇩🇪',
  },
  {
    year: 2010,
    event: 'Inde EVMs : académiciens prouvent possibilité de manipulation à distance',
    country: '🇮🇳',
  },
  {
    year: 2019,
    event: 'Suisse : Post-Vote (e-voting national) retire son système après audit',
    country: '🇨🇭',
  },
  {
    year: 2020,
    event: 'Voatz (vote mobile US) : audit Harvard révèle 3 vulnérabilités critiques',
    country: '🇺🇸',
  },
];

const WhyHardSection: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="why-hard-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      ❌ {t('tech.whyHardTitle')}
    </CardHeader>
    <CardBody>
      <p className="text-muted-foreground" style={{ fontSize: '0.85rem' }}>
        {t('tech.whyHardDesc')}
      </p>
      <div style={{ borderLeft: '3px solid #dee2e6', paddingLeft: 16 }}>
        {INCIDENTS.map((inc) => (
          <div key={inc.year} className="mb-2">
            <span className="text-muted-foreground me-2" style={{ fontSize: '0.75rem' }}>
              {inc.year} {inc.country}
            </span>
            <span style={{ fontSize: '0.82rem' }}>{inc.event}</span>
          </div>
        ))}
      </div>
    </CardBody>
  </Card>
);

// ── Section 2 — E2E-V demo ────────────────────────────────────────────────────

const STEPS = [
  { id: 'vote', icon: '🗳️' },
  { id: 'encrypt', icon: '🔒' },
  { id: 'board', icon: '📋' },
  { id: 'sum', icon: '∑' },
  { id: 'result', icon: '✅' },
];

const E2EVSection: React.FC<{ t: (k: string) => string }> = ({ t }) => {
  const [step, setStep] = useState(0);
  const sim = $api.useMutation('post', '/api/v2/tech/e2e-demo');
  const data: E2EData | null = (sim.data as E2EData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('tech.error') : null;

  const runDemo = useCallback(() => {
    setStep(0);
    sim.mutate(
      {
        body: {
          candidates: ['Alice', 'Bob', 'Carol'],
          num_voters: 10,
          seed: 42,
          user_vote: 'Alice',
        },
      },
      {
        onSuccess: () => setStep(1),
      }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [t, sim]);

  const advance = () => setStep((s) => Math.min(s + 1, STEPS.length - 1));

  return (
    <Card className="mb-4" data-testid="e2e-section">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
        🔐 {t('tech.e2eTitle')}
      </CardHeader>
      <CardBody>
        <p style={{ fontSize: '0.85rem' }}>{t('tech.e2eDesc')}</p>

        {/* Step indicator */}
        <div className="flex gap-2 mb-3 flex-wrap">
          {STEPS.map((s, i) => (
            <div
              key={s.id}
              className={`d-flex align-items-center gap-1 px-2 py-1 rounded ${
                i < step
                  ? 'bg-[#198754] text-white'
                  : i === step && step > 0
                    ? 'bg-primary text-white'
                    : 'bg-slate-100 text-muted-foreground'
              }`}
              style={{ fontSize: '0.78rem', cursor: 'default' }}
              data-testid={`step-${s.id}`}
            >
              {s.icon} {t(`tech.e2eStep${i}`)}
            </div>
          ))}
        </div>

        {!data && !loading && !error && (
          <Button variant="primary" onClick={runDemo} data-testid="run-e2e-btn">
            {t('tech.e2eRun')}
          </Button>
        )}
        {loading && <Spinner size="sm" />}
        {error && <Alert variant="danger">{error}</Alert>}

        {data && (
          <div data-testid="e2e-result">
            {/* Step 1 — Encryption */}
            {step >= 1 && (
              <div className="mb-3 p-3 rounded" style={{ background: '#f8f9fa' }}>
                <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
                  🔒 {t('tech.e2eEncryptTitle')}
                </div>
                <div className="flex flex-wrap gap-2">
                  {data.encrypted_ballots.slice(0, 5).map((b) => (
                    <div
                      key={b.voter_id}
                      className="border border-border rounded p-2"
                      style={{ fontSize: '0.72rem', background: '#fff', minWidth: 120 }}
                      data-testid="encrypted-ballot"
                    >
                      <div className="text-muted-foreground">#{b.voter_id}</div>
                      <code style={{ color: '#6f42c1' }}>{b.encrypted}</code>
                      <div className="text-muted-foreground mt-1">
                        {t('tech.e2eCode')}: {b.code}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Step 2 — Public board */}
            {step >= 2 && (
              <div
                className="mb-3 p-3 rounded border border-border"
                style={{ background: '#fffbf0' }}
              >
                <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                  📋 {t('tech.e2eBoardTitle')}
                </div>
                <p style={{ fontSize: '0.75rem', color: '#6c757d' }}>{t('tech.e2eBoardDesc')}</p>
                <div className="flex flex-wrap gap-1" data-testid="verification-board">
                  {data.verification_demonstration.board_excerpt.map((code, i) => (
                    <Badge
                      key={i}
                      variant="light"
                      style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}
                    >
                      {code}
                    </Badge>
                  ))}
                  <Badge variant="warning" style={{ fontFamily: 'monospace', fontSize: '0.7rem' }}>
                    ← {t('tech.e2eYourCode')}: {data.verification_demonstration.sample_code}
                  </Badge>
                </div>
              </div>
            )}

            {/* Step 3 — Homomorphic sum */}
            {step >= 3 && (
              <div
                className="mb-3 p-3 rounded border border-border border-info"
                style={{ background: '#f0f8ff' }}
              >
                <div className="font-semibold mb-1" style={{ fontSize: '0.82rem' }}>
                  ∑ {t('tech.e2eSumTitle')}
                </div>
                <p style={{ fontSize: '0.75rem', color: '#6c757d' }}>{t('tech.e2eSumDesc')}</p>
                <code style={{ fontSize: '0.75rem' }}>
                  {data.encrypted_ballots
                    .slice(0, 3)
                    .map((b) => b.encrypted)
                    .join(' + ')}{' '}
                  + … = 🔒[…]
                </code>
              </div>
            )}

            {/* Step 4 — Result */}
            {step >= 4 && (
              <div
                className="mb-3 p-3 rounded border border-border border-success"
                style={{ background: '#f0fff4' }}
                data-testid="e2e-final-result"
              >
                <div className="font-semibold mb-2" style={{ fontSize: '0.82rem' }}>
                  ✅ {t('tech.e2eResultTitle')}
                </div>
                <div className="flex gap-3 flex-wrap">
                  {Object.entries(data.aggregate_result)
                    .sort((a, b) => b[1] - a[1])
                    .map(([cand, count]) => (
                      <div key={cand} className="text-center">
                        <div style={{ fontWeight: 600 }}>{cand}</div>
                        <div style={{ fontSize: '1.2rem', color: '#198754' }}>{count}</div>
                      </div>
                    ))}
                </div>
                <Alert variant="success" className="mt-2 mb-0" style={{ fontSize: '0.75rem' }}>
                  {data.privacy_guarantee}
                </Alert>
              </div>
            )}

            {step < STEPS.length - 1 && (
              <Button
                variant="outline-primary"
                size="sm"
                onClick={advance}
                data-testid="next-step-btn"
              >
                {t('tech.e2eNext')} →
              </Button>
            )}
            {step === STEPS.length - 1 && (
              <Button
                variant="outline-secondary"
                size="sm"
                onClick={() => {
                  sim.reset();
                  setStep(0);
                }}
              >
                {t('tech.e2eReset')}
              </Button>
            )}
          </div>
        )}
      </CardBody>
    </Card>
  );
};

// ── Section 3 — Blockchain table ──────────────────────────────────────────────

const BLOCKCHAIN_DATA = [
  {
    mech: 'Token voting 1t1v',
    usedBy: 'Compound, Uniswap',
    method: 'Plurality pondérée',
    solves: 'Coordination décentralisée',
    limit: 'Whale dominance',
  },
  {
    mech: 'Conviction Voting',
    usedBy: 'Polkadot, Kusama',
    method: 'Temps × tokens',
    solves: 'Achats flash',
    limit: 'Toujours des whales',
  },
  {
    mech: 'Quadratic Funding',
    usedBy: 'Gitcoin, Optimism',
    method: '√ de contributions',
    solves: 'Biens communs équitables',
    limit: 'Sybil attacks',
  },
  {
    mech: 'Liquid Democracy',
    usedBy: 'DemocracyEarth',
    method: 'Délégation transitive',
    solves: 'Expertise + participation',
    limit: 'Super-votants',
  },
  {
    mech: 'Auto-amendment',
    usedBy: 'Tezos',
    method: 'Borda modifié',
    solves: 'Le protocole évolue lui-même',
    limit: 'Méta-cycles',
  },
];

const BlockchainTable: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="blockchain-table-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      ⛓ {t('tech.blockchainTitle')}
    </CardHeader>
    <CardBody className="p-0">
      <Table
        className="[&_th]:p-2 [&_td]:p-2 [&_th]:text-left [&_td]:border-t [&_th]:border-b [&_td]:border-border [&_th]:border-border [&_*]:align-middle [&_tbody_tr:hover]:bg-muted/50 mb-0"
        style={{ fontSize: '0.8rem' }}
      >
        <thead className="table-light">
          <tr>
            <th>{t('tech.blkMechanism')}</th>
            <th>{t('tech.blkUsedBy')}</th>
            <th>{t('tech.blkMethod')}</th>
            <th>{t('tech.blkSolves')}</th>
            <th>{t('tech.blkLimit')}</th>
          </tr>
        </thead>
        <tbody>
          {BLOCKCHAIN_DATA.map((row) => (
            <tr key={row.mech}>
              <td>
                <strong>{row.mech}</strong>
              </td>
              <td className="text-muted-foreground">{row.usedBy}</td>
              <td>
                <code style={{ fontSize: '0.75rem' }}>{row.method}</code>
              </td>
              <td style={{ color: '#198754' }}>{row.solves}</td>
              <td style={{ color: '#dc3545' }}>{row.limit}</td>
            </tr>
          ))}
        </tbody>
      </Table>
    </CardBody>
  </Card>
);

// ── Section 4 — Pol.is demo ───────────────────────────────────────────────────

const DEFAULT_STATEMENTS = [
  'Les plateformes de location courte durée doivent être réglementées.',
  'Les hôtes devraient payer des taxes identiques aux hôtels.',
  'Les VTC doivent respecter les mêmes obligations que les taxis.',
  'La tarification dynamique est équitable pour les consommateurs.',
  'La sécurité des passagers prime sur la commodité des plateformes.',
  'Les travailleurs de plateforme méritent des protections sociales.',
  "L'innovation technologique devrait primer sur la réglementation.",
  'Les gouvernements locaux devraient contrôler les plateformes.',
  'La concurrence entre plateformes bénéficie aux consommateurs.',
  'Les données des utilisateurs appartiennent aux utilisateurs, pas aux plateformes.',
];

const PolisSection: React.FC<{ t: (k: string) => string }> = ({ t }) => {
  const [numClusters, setNumClusters] = useState(3);
  const [ideology, setIdeology] = useState('random');
  const [numParticipants, setNumParticipants] = useState(100);
  const sim = $api.useMutation('post', '/api/v2/tech/polis-simulation');
  const data: PolisData | null = (sim.data as PolisData | undefined) ?? null;
  const loading = sim.isPending;
  const error = sim.isError ? t('tech.error') : null;

  const run = useCallback(() => {
    sim.mutate({
      body: {
        statements: DEFAULT_STATEMENTS,
        num_participants: numParticipants,
        ideology,
        seed: 42,
        num_clusters: numClusters,
      },
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [numClusters, ideology, numParticipants, t, sim]);

  return (
    <Card className="mb-4" data-testid="polis-section">
      <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
        🌐 {t('tech.polisTitle')}
      </CardHeader>
      <CardBody>
        <p style={{ fontSize: '0.85rem' }}>{t('tech.polisDesc')}</p>

        <Row className="g-2 mb-3 items-end">
          <Col xs={6} md={3}>
            <label className="mb-1 inline-block text-sm mb-0">{t('tech.polisIdeology')}</label>
            <Select
              size="sm"
              value={ideology}
              onChange={(e) => setIdeology(e.target.value)}
              data-testid="ideology-select"
            >
              <option value="random">{t('tech.ideologyRandom')}</option>
              <option value="polarized">{t('tech.ideologyPolarized')}</option>
            </Select>
          </Col>
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('tech.polisClusters')}</label>
            <Control
              type="number"
              size="sm"
              min={1}
              max={5}
              value={numClusters}
              onChange={(e) => setNumClusters(Math.max(1, Math.min(5, Number(e.target.value))))}
              data-testid="num-clusters-input"
            />
          </Col>
          <Col xs={6} md={2}>
            <label className="mb-1 inline-block text-sm mb-0">{t('tech.polisParticipants')}</label>
            <Control
              type="number"
              size="sm"
              min={20}
              max={500}
              step={10}
              value={numParticipants}
              onChange={(e) =>
                setNumParticipants(Math.max(20, Math.min(500, Number(e.target.value))))
              }
            />
          </Col>
          <Col xs="auto">
            <Button variant="primary" onClick={run} disabled={loading} data-testid="run-polis-btn">
              {loading ? <Spinner size="sm" /> : t('tech.polisRun')}
            </Button>
          </Col>
        </Row>

        {!data && !loading && !error && (
          <Alert variant="info" role="alert">
            {t('tech.polisPrompt')}
          </Alert>
        )}
        {error && <Alert variant="danger">{error}</Alert>}

        {data && (
          <>
            {data.consensus_statements.length > 0 && (
              <Alert variant="success" className="mb-3" style={{ fontSize: '0.8rem' }}>
                <strong>{`${data.consensus_statements.length} ${t('tech.consensusMessage')}`}</strong>
              </Alert>
            )}
            <PoliticalClusterMap data={data} />
          </>
        )}
      </CardBody>
    </Card>
  );
};

// ── Section "3 approches" ─────────────────────────────────────────────────────

const ThreeApproachesSection: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="three-approaches-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      ⚡ {t('tech.approachesTitle')}
    </CardHeader>
    <CardBody>
      <Row className="g-3">
        <Col xs={12} md={4}>
          <div className="border border-border border-danger rounded p-3 h-full">
            <div className="font-bold mb-2 text-[#dc3545]">❌ Vote par SMS / App mobile</div>
            <div style={{ fontSize: '0.8rem' }}>
              Le terminal de l'électeur peut être compromis. Si votre téléphone est infecté, votre
              vote peut être modifié AVANT chiffrement — aucune vérification possible.
            </div>
            <Badge variant="danger" className="mt-2" style={{ fontSize: '0.65rem' }}>
              Non vérifiable · Non auditable
            </Badge>
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="border border-border border-warning rounded p-3 h-full">
            <div className="font-bold mb-2" style={{ color: '#856404' }}>
              ⚠️ Vote par Blockchain
            </div>
            <div style={{ fontSize: '0.8rem' }}>
              Toutes les transactions sont publiques sur la blockchain → votre vote est visible de
              tous. Parfait pour la gouvernance de protocole, incompatible avec le secret du
              bulletin dans une démocratie.
            </div>
            <Badge variant="warning" className="mt-2" style={{ fontSize: '0.65rem' }}>
              Transparent · Pas secret
            </Badge>
          </div>
        </Col>
        <Col xs={12} md={4}>
          <div className="border border-border border-success rounded p-3 h-full">
            <div className="font-bold mb-2 text-[#198754]">✅ Vote E2E-V (ElectionGuard)</div>
            <div style={{ fontSize: '0.8rem' }}>
              Chiffrement homomorphe : les bulletins sont additionnés SANS être déchiffrés
              individuellement. Chaque électeur vérifie que son bulletin est compté, sans révéler
              son choix. Open source, testé en conditions réelles.
            </div>
            <Badge variant="success" className="mt-2" style={{ fontSize: '0.65rem' }}>
              Secret · Vérifiable · Auditable
            </Badge>
          </div>
        </Col>
      </Row>
    </CardBody>
  </Card>
);

// ── Section interactive E2E-V (E2EVDemo) ─────────────────────────────────────

const E2EVInteractiveSection: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="e2ev-interactive-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      🔐 {t('tech.e2eInteractiveTitle')}
    </CardHeader>
    <CardBody>
      <p style={{ fontSize: '0.85rem' }}>{t('tech.e2eInteractiveDesc')}</p>
      <E2EVDemo candidates={['Alice', 'Bob', 'Carol']} seed={42} />
    </CardBody>
  </Card>
);

// ── Section pays (country comparison) ────────────────────────────────────────

const COUNTRY_DATA = [
  {
    flag: '🇪🇪',
    country: 'Estonie',
    tech: 'Carte ID + PKI',
    secret: '✓',
    verif: 'Partiel',
    used: '51% en 2023',
  },
  {
    flag: '🇫🇮',
    country: 'Finlande',
    tech: 'ElectionGuard E2E-V',
    secret: '✓',
    verif: '✓',
    used: 'Tests 2023',
  },
  {
    flag: '🇺🇸',
    country: 'USA (comtés)',
    tech: 'ElectionGuard E2E-V',
    secret: '✓',
    verif: '✓',
    used: 'Déploiements réels',
  },
  {
    flag: '⛓',
    country: 'DAO (Ethereum)',
    tech: 'On-chain',
    secret: '✗',
    verif: '✓',
    used: 'Compound, Uniswap',
  },
  { flag: '🇫🇷', country: 'France', tech: 'Papier', secret: '✓', verif: '✗', used: '100%' },
];

const CountryComparisonSection: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="country-comparison-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      🌍 {t('tech.countryTableTitle')}
    </CardHeader>
    <CardBody className="p-0">
      <div className="table-responsive">
        <table className="table table-hover table-sm mb-0" style={{ fontSize: '0.82rem' }}>
          <thead className="table-light">
            <tr>
              <th>Pays / Système</th>
              <th>Technologie</th>
              <th title="Secret du bulletin">🔒 Secret</th>
              <th title="Vérifiable par l'électeur">🔍 Vérifiable</th>
              <th>Utilisé</th>
            </tr>
          </thead>
          <tbody>
            {COUNTRY_DATA.map((row) => (
              <tr key={row.country}>
                <td>
                  <strong>
                    {row.flag} {row.country}
                  </strong>
                </td>
                <td>
                  <code style={{ fontSize: '0.75rem' }}>{row.tech}</code>
                </td>
                <td style={{ color: row.secret === '✓' ? '#198754' : '#dc3545' }}>{row.secret}</td>
                <td
                  style={{
                    color:
                      row.verif === '✓' ? '#198754' : row.verif === '✗' ? '#dc3545' : '#fd7e14',
                  }}
                >
                  {row.verif}
                </td>
                <td className="text-muted-foreground">{row.used}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </CardBody>
  </Card>
);

// ── Section "Pourquoi la France..." ──────────────────────────────────────────

const WhyFranceSection: React.FC<{ t: (k: string) => string }> = ({ t }) => (
  <Card className="mb-4" data-testid="why-france-section">
    <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
      🇫🇷 {t('tech.whyFranceTitle')}
    </CardHeader>
    <CardBody>
      <Row className="g-3">
        <Col xs={12} md={6}>
          <div className="font-semibold text-[#198754] mb-2" style={{ fontSize: '0.85rem' }}>
            ✓ Ce qui existe déjà
          </div>
          <ul style={{ fontSize: '0.82rem', paddingLeft: 18 }}>
            <li>FranceConnect : identité numérique nationale (utilisée par 40M de Français)</li>
            <li>ElectionGuard est open source, gratuit, audité par NIST</li>
            <li>Vote par internet déjà pour Français de l'étranger (législatives)</li>
            <li>Infrastructure cybersécurité ANSSI de haut niveau</li>
          </ul>
        </Col>
        <Col xs={12} md={6}>
          <div className="font-semibold text-[#dc3545] mb-2" style={{ fontSize: '0.85rem' }}>
            ✗ Ce qui manque encore
          </div>
          <ul style={{ fontSize: '0.82rem', paddingLeft: 18 }}>
            <li>Déploiement à l'échelle 48M votants (vs 1.4M en Estonie)</li>
            <li>Confiance institutionnelle (le Conseil Constitutionnel reste sceptique)</li>
            <li>Résistance aux cyberattaques d'État (Russie, Chine)</li>
            <li>20 ans d'expérience (l'Estonie a commencé en 2005)</li>
          </ul>
        </Col>
      </Row>
      <Alert variant="info" className="mt-3 mb-0" style={{ fontSize: '0.8rem' }}>
        <strong>En résumé :</strong> L'Estonie a 1.4M d'habitants et 20 ans d'expérience. La France
        a 48M de votants et zéro déploiement réel à grande échelle. La technologie existe — c'est la
        confiance institutionnelle et l'échelle qui manquent.
      </Alert>
    </CardBody>
  </Card>
);

// ── Main page ─────────────────────────────────────────────────────────────────

const TechDemocracyPage: React.FC = () => {
  const { t } = useTranslation();
  useMetaTags({
    title: 'Solutions technologiques — Vote Lab',
    description:
      'E2E-V, Pol.is, blockchain governance : comment la technologie peut améliorer les systèmes électoraux.',
  });

  return (
    <Container className="py-4" style={{ maxWidth: 960 }}>
      <h2 className="font-bold mb-1">💻 {t('tech.pageTitle')}</h2>
      <p className="text-muted-foreground mb-4" style={{ fontSize: '0.9rem' }}>
        {t('tech.pageSubtitle')}
      </p>

      <WhyHardSection t={t} />
      <ThreeApproachesSection t={t} />
      <E2EVInteractiveSection t={t} />
      <CountryComparisonSection t={t} />
      <WhyFranceSection t={t} />
      <BlockchainTable t={t} />

      {/* ── Pol.is avec évaluation des candidats ── */}
      <Card className="mb-4" data-testid="polis-panel-section">
        <CardHeader className="block space-y-0 border-b border-border px-4 py-2 font-bold">
          🌐 {t('tech.polisTitle')}
        </CardHeader>
        <CardBody>
          <p style={{ fontSize: '0.85rem' }}>{t('tech.polisDesc')}</p>
          <ElectionProvider>
            <PolisPanel />
          </ElectionProvider>
        </CardBody>
      </Card>

      <PolisSection t={t} />
    </Container>
  );
};

export default TechDemocracyPage;
