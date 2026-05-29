import React, { useState } from 'react';
import { Alert, Badge, Button, Card, Col, Container, Row, Tab, Tabs } from 'react-bootstrap';
import { useMetaTags } from '../hooks/useMetaTags';

// Public API /api/v1 is served by FastAPI as of Phase 4.5.a.4 (port 4434 in
// dev). Behind the prod reverse proxy this is a single origin; the constant is
// dev-facing — it drives the live openapi.json links and the copy-paste curl
// examples shown to external researchers.
const API_BASE = 'http://localhost:4434';

// ── Copy-to-clipboard button ─────────────────────────────────────────────────

const CopyButton: React.FC<{ text: string }> = ({ text }) => {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      variant={copied ? 'success' : 'outline-secondary'}
      size="sm"
      style={{ float: 'right', fontSize: '0.72rem', padding: '2px 8px' }}
      onClick={async () => {
        try { await navigator.clipboard.writeText(text); } catch { /* ignore */ }
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      aria-label="Copier la commande"
    >
      {copied ? '✓ Copié' : '📋 Copier'}
    </Button>
  );
};

// ── Endpoint card ─────────────────────────────────────────────────────────────

interface Param { name: string; type: string; range?: string; desc: string; required?: boolean; default?: string }

interface EndpointProps {
  method: 'GET' | 'POST';
  path: string;
  summary: string;
  description: string;
  rateLimit?: string;
  params?: Param[];
  curlExample: string;
  responseExample: string;
}

const EndpointCard: React.FC<EndpointProps> = ({
  method, path, summary, description, rateLimit, params, curlExample, responseExample,
}) => (
  <Card className="mb-4 shadow-sm">
    <Card.Header className="d-flex align-items-center gap-2 flex-wrap">
      <Badge
        bg={method === 'GET' ? 'success' : 'primary'}
        style={{ fontSize: '0.8rem', padding: '4px 10px', fontFamily: 'monospace' }}
      >
        {method}
      </Badge>
      <code style={{ fontSize: '0.95rem', fontWeight: 600 }}>{path}</code>
      {rateLimit && (
        <Badge bg="warning" text="dark" style={{ fontSize: '0.72rem', marginLeft: 'auto' }}>
          ⏱ {rateLimit}
        </Badge>
      )}
    </Card.Header>
    <Card.Body>
      <h6 className="fw-bold mb-1">{summary}</h6>
      <p className="text-muted mb-3" style={{ fontSize: '0.88rem' }}>{description}</p>

      {params && params.length > 0 && (
        <div className="mb-3">
          <div className="fw-semibold small mb-2">Paramètres</div>
          <table className="table table-sm" style={{ fontSize: '0.82rem' }}>
            <thead className="table-light">
              <tr><th>Nom</th><th>Type</th><th>Plage / Options</th><th>Défaut</th><th>Description</th></tr>
            </thead>
            <tbody>
              {params.map((p) => (
                <tr key={p.name}>
                  <td><code>{p.name}</code>{p.required && <span className="text-danger ms-1">*</span>}</td>
                  <td><code>{p.type}</code></td>
                  <td className="text-muted">{p.range ?? '—'}</td>
                  <td className="text-muted">{p.default ?? '—'}</td>
                  <td>{p.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Tabs defaultActiveKey="curl" className="mb-2" style={{ fontSize: '0.82rem' }}>
        <Tab eventKey="curl" title="curl">
          <div style={{ position: 'relative', background: '#1e1e1e', borderRadius: 6, padding: '12px 14px' }}>
            <CopyButton text={curlExample} />
            <pre style={{ color: '#d4d4d4', margin: 0, fontSize: '0.8rem', overflowX: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {curlExample}
            </pre>
          </div>
        </Tab>
        <Tab eventKey="response" title="Exemple de réponse">
          <div style={{ position: 'relative', background: '#1e1e1e', borderRadius: 6, padding: '12px 14px' }}>
            <CopyButton text={responseExample} />
            <pre style={{ color: '#9cdcfe', margin: 0, fontSize: '0.8rem', overflowX: 'auto', maxHeight: 200 }}>
              {responseExample}
            </pre>
          </div>
        </Tab>
      </Tabs>
    </Card.Body>
  </Card>
);

// ── Data ──────────────────────────────────────────────────────────────────────

const ENDPOINTS: EndpointProps[] = [
  {
    method: 'GET',
    path: '/api/v1/methods',
    summary: 'Lister les méthodes de vote',
    description: 'Retourne le catalogue complet des 16+ méthodes de vote supportées par le moteur Vote Lab, avec leur famille et référence académique.',
    params: [
      { name: 'family', type: 'string', range: 'ranked | score | intensity', desc: 'Filtrer par famille de méthode', default: '(toutes)' },
    ],
    curlExample: `curl "${API_BASE}/api/v1/methods"`,
    responseExample: `{
  "count": 18,
  "families": ["intensity", "ranked", "score"],
  "methods": [
    { "key": "plurality", "name": "Plurality (FPTP)", "family": "ranked", "ref": "Duverger (1954)" },
    { "key": "borda",     "name": "Borda Count",      "family": "ranked", "ref": "Borda (1781)" },
    { "key": "schulze",   "name": "Schulze Method",   "family": "ranked", "ref": "Schulze (2011)" }
  ]
}`,
  },
  {
    method: 'POST',
    path: '/api/v1/simulate',
    summary: 'Lancer une simulation',
    description: 'Exécute une simulation multi-méthodes sur une population synthétique générée par le modèle spatial de Vote Lab. Les utilités sont calculées sur 20 enjeux politiques.',
    rateLimit: '10 req/min par IP',
    params: [
      { name: 'num_candidates',        type: 'int',    range: '2–8',    desc: 'Nombre de candidats',            default: '4' },
      { name: 'num_voters',            type: 'int',    range: '50–2000', desc: 'Nombre d\'électeurs',           default: '500' },
      { name: 'methods',               type: 'array|string', range: '"all" ou liste de clés', desc: 'Méthodes à simuler', default: '"all"' },
      { name: 'ideology_distribution', type: 'string', range: 'random|centrist|polarized|left_skewed|right_skewed', desc: 'Distribution idéologique', default: '"random"' },
    ],
    curlExample: `curl -X POST "${API_BASE}/api/v1/simulate" \\
  -H "Content-Type: application/json" \\
  -d '{"num_candidates": 4, "num_voters": 500, "methods": ["plurality", "borda", "schulze"]}'`,
    responseExample: `{
  "condorcet_winner": "Alice",
  "methods": {
    "plurality": {
      "winner": "Alice",
      "bayesian_regret": 0.1234,
      "majority_satisfaction": 0.72,
      "condorcet_consistent": true,
      "strategic_vulnerability": 0.28
    },
    "borda": {
      "winner": "Bob",
      "bayesian_regret": 0.0876,
      "majority_satisfaction": 0.81,
      "condorcet_consistent": false,
      "strategic_vulnerability": 0.19
    }
  }
}`,
  },
  {
    method: 'POST',
    path: '/api/v1/compare',
    summary: 'Comparaison avec vote blanc',
    description: 'Comme /simulate mais avec une règle constitutionnelle de vote blanc optionnelle. Retourne l\'impact de la règle sur chaque méthode.',
    rateLimit: '5 req/min par IP',
    params: [
      { name: 'num_candidates',        type: 'int',    range: '2–8',    desc: 'Nombre de candidats',  default: '4' },
      { name: 'num_voters',            type: 'int',    range: '50–2000', desc: 'Nombre d\'électeurs', default: '500' },
      { name: 'blank_rule',            type: 'string', range: 'symbolic|competitive|threshold_30|majority_required', desc: 'Règle du vote blanc (optionnelle)', default: '(désactivé)' },
      { name: 'methods',               type: 'array|string', range: '"all" ou liste', desc: 'Méthodes', default: '"all"' },
      { name: 'ideology_distribution', type: 'string', range: 'random|centrist|polarized|…', desc: 'Distribution idéologique', default: '"random"' },
    ],
    curlExample: `curl -X POST "${API_BASE}/api/v1/compare" \\
  -H "Content-Type: application/json" \\
  -d '{"num_candidates": 3, "num_voters": 800, "blank_rule": "threshold_30"}'`,
    responseExample: `{
  "condorcet_winner": "Alice",
  "blank_pct": 0.0312,
  "methods": {
    "plurality": {
      "winner": "Alice",
      "bayesian_regret": 0.11,
      "blank_rule_applied": {
        "winner": "Alice",
        "blank_triggered": false,
        "consequence": "Le vote blanc (3.1%) reste sous le seuil de 30%.",
        "blank_pct": 0.0312,
        "rule": "threshold_30"
      }
    }
  }
}`,
  },
  {
    method: 'GET',
    path: '/api/v1/real-elections',
    summary: 'Élections historiques',
    description: 'Retourne les métadonnées des élections réelles incluses dans Vote Lab : France 2002/2022, USA 1992, UK 2015, etc., avec le taux de vote blanc estimé.',
    curlExample: `curl "${API_BASE}/api/v1/real-elections"`,
    responseExample: `{
  "count": 5,
  "elections": [
    {
      "key": "france_2022",
      "name": "Élection présidentielle française — 1er tour",
      "year": 2022,
      "country": "France",
      "num_candidates": 12,
      "estimated_blank_pct": 0.025,
      "source": "Ministère de l'Intérieur — résultats officiels 10 avril 2022"
    }
  ]
}`,
  },
];

// ── Use cases ─────────────────────────────────────────────────────────────────

const USE_CASES = [
  {
    icon: '🐍',
    title: 'Python — analyse de recherche',
    code: `import requests

BASE = "${API_BASE}/api/v1"

# Compare 5 methods on a 4-candidate election
resp = requests.post(f"{BASE}/simulate", json={
    "num_candidates": 4,
    "num_voters": 1000,
    "methods": ["plurality", "borda", "schulze", "irv", "approval"],
    "ideology_distribution": "polarized",
})
data = resp.json()
print({m: d["winner"] for m, d in data["methods"].items()})
# → {'plurality': 'Alice', 'borda': 'Bob', 'schulze': 'Alice', ...}`,
  },
  {
    icon: '📊',
    title: 'R — simulation Monte Carlo',
    code: `library(httr2)

simulate_once <- function(n_cands, n_voters) {
  req <- request("${API_BASE}/api/v1/simulate") |>
    req_body_json(list(num_candidates = n_cands, num_voters = n_voters,
                       methods = c("plurality", "borda")))
  resp <- req_perform(req)
  resp_body_json(resp)
}

# Run 50 simulations and compare winners
results <- replicate(50, simulate_once(4, 500), simplify = FALSE)
winners <- sapply(results, function(r) r$methods$plurality$winner)
table(winners)`,
  },
];

// ── ApiDocsPage ───────────────────────────────────────────────────────────────

const ApiDocsPage: React.FC = () => {
  useMetaTags({
    title: 'API Documentation — Vote Lab',
    description: 'Public REST API for integrating Vote Lab\'s voting simulation engine into research projects.',
  });

  return (
    <Container className="py-4" style={{ maxWidth: 960 }}>
      {/* Header */}
      <div className="d-flex align-items-start justify-content-between mb-3 flex-wrap gap-2">
        <div>
          <h2 className="mb-1 fw-bold">🔌 API Publique — Vote Lab</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.9rem' }}>
            Intégrez le moteur de simulation électorale de Vote Lab dans vos projets de recherche.
            Aucune authentification requise.
          </p>
        </div>
        <div className="d-flex gap-2">
          <Button
            variant="outline-secondary"
            size="sm"
            as="a"
            href={`${API_BASE}/api/v1/openapi.json`}
            target="_blank"
            rel="noopener noreferrer"
          >
            📄 openapi.json
          </Button>
        </div>
      </div>

      {/* Base URL */}
      <Alert variant="secondary" className="mb-4 py-2">
        <strong>Base URL :</strong>{' '}
        <code>{API_BASE}/api/v1</code>
        {' · '}
        <span className="text-muted">Toutes les réponses sont en JSON · UTF-8</span>
      </Alert>

      {/* Rate limits info */}
      <Card className="mb-4 border-warning">
        <Card.Body className="py-2">
          <div className="d-flex gap-4 flex-wrap" style={{ fontSize: '0.85rem' }}>
            <span>⏱ <strong>POST /simulate</strong> : 10 requêtes/min par IP</span>
            <span>⏱ <strong>POST /compare</strong> : 5 requêtes/min par IP</span>
            <span>✓ GET endpoints : illimités</span>
          </div>
        </Card.Body>
      </Card>

      <Tabs defaultActiveKey="endpoints" className="mb-4">
        {/* Endpoints tab */}
        <Tab eventKey="endpoints" title="📍 Endpoints">
          {ENDPOINTS.map((ep) => (
            <EndpointCard key={ep.path} {...ep} />
          ))}
        </Tab>

        {/* Code examples tab */}
        <Tab eventKey="examples" title="💻 Exemples de code">
          <Row className="g-4">
            {USE_CASES.map((uc) => (
              <Col key={uc.title} md={12}>
                <Card>
                  <Card.Header className="fw-semibold">
                    {uc.icon} {uc.title}
                  </Card.Header>
                  <Card.Body className="p-0">
                    <div style={{ position: 'relative' }}>
                      <CopyButton text={uc.code} />
                      <pre style={{
                        background: '#1e1e1e', color: '#9cdcfe',
                        margin: 0, padding: '16px 14px',
                        fontSize: '0.8rem', borderRadius: '0 0 8px 8px',
                        overflowX: 'auto',
                      }}>
                        {uc.code}
                      </pre>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        </Tab>

        {/* Use cases tab */}
        <Tab eventKey="usecases" title="🎓 Cas d'usage">
          <Row className="g-3">
            {[
              { title: 'Comparaison systématique', desc: 'Simulez la même élection sous 16 méthodes et comparez les vainqueurs pour illustrer le théorème d\'impossibilité d\'Arrow dans vos cours ou publications.' },
              { title: 'Analyse Monte Carlo', desc: 'Répétez 1 000 simulations avec différentes distributions idéologiques et calculez la robustesse de chaque méthode à la variance de l\'électorat.' },
              { title: 'Étude du vote blanc', desc: 'Utilisez /compare avec blank_rule=threshold_30 pour modéliser l\'impact de la règle colombienne (> 50% → nouvelle élection) sur différentes configurations.' },
              { title: 'Dataset pour ML', desc: 'Générez des milliers de simulations avec graine fixe pour entraîner des modèles prédictifs sur les comportements des méthodes de vote.' },
              { title: 'Enseignement interactif', desc: 'Intégrez Vote Lab dans un notebook Jupyter ou une app Shiny pour montrer en temps réel comment le résultat change selon la méthode choisie.' },
              { title: 'Réplication de résultats', desc: 'Utilisez ideology_distribution=polarized pour reproduire des scénarios proches des élections de 2002 en France ou 1992 aux USA.' },
            ].map(({ title, desc }) => (
              <Col md={6} key={title}>
                <Card className="h-100">
                  <Card.Body>
                    <h6 className="fw-bold">{title}</h6>
                    <p className="text-muted mb-0" style={{ fontSize: '0.85rem' }}>{desc}</p>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        </Tab>
      </Tabs>

      {/* Footer */}
      <div className="text-muted text-center mt-4" style={{ fontSize: '0.78rem' }}>
        Vote Lab est open-source · Licence MIT ·{' '}
        <a href="https://github.com/Burbanit0/Vote-App" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        {' · '}
        <a href={`${API_BASE}/api/v1/openapi.json`} target="_blank" rel="noopener noreferrer">
          OpenAPI 3.0
        </a>
      </div>
    </Container>
  );
};

export default ApiDocsPage;
