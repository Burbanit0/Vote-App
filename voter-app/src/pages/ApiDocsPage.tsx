import React, { useState } from 'react';
import { useMetaTags } from '../hooks/useMetaTags';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

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
      className="float-right h-auto px-2 py-0.5 text-[0.72rem]"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
        } catch {
          /* ignore */
        }
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

interface Param {
  name: string;
  type: string;
  range?: string;
  desc: string;
  required?: boolean;
  default?: string;
}

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
  method,
  path,
  summary,
  description,
  rateLimit,
  params,
  curlExample,
  responseExample,
}) => (
  <Card className="mb-6 shadow-sm">
    <CardHeader className="flex flex-row flex-wrap items-center gap-2 p-6 py-3">
      <Badge
        variant={method === 'GET' ? 'success' : 'primary'}
        className="px-2.5 py-1 font-mono text-[0.8rem]"
      >
        {method}
      </Badge>
      <code className="text-[0.95rem] font-semibold">{path}</code>
      {rateLimit && (
        <Badge variant="warning" className="ml-auto text-[0.72rem]">
          ⏱ {rateLimit}
        </Badge>
      )}
    </CardHeader>
    <CardContent className="p-6">
      <h6 className="mb-1 font-bold">{summary}</h6>
      <p className="mb-4 text-[0.88rem] text-muted-foreground">{description}</p>

      {params && params.length > 0 && (
        <div className="mb-4">
          <div className="mb-2 text-sm font-semibold">Paramètres</div>
          <table className="w-full border-collapse text-[0.82rem]">
            <thead className="bg-muted">
              <tr className="border-b border-border [&>th]:p-1.5 [&>th]:text-left">
                <th>Nom</th>
                <th>Type</th>
                <th>Plage / Options</th>
                <th>Défaut</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {params.map((p) => (
                <tr key={p.name} className="border-b border-border [&>td]:p-1.5">
                  <td>
                    <code>{p.name}</code>
                    {p.required && <span className="ml-1 text-[#dc3545]">*</span>}
                  </td>
                  <td>
                    <code>{p.type}</code>
                  </td>
                  <td className="text-muted-foreground">{p.range ?? '—'}</td>
                  <td className="text-muted-foreground">{p.default ?? '—'}</td>
                  <td>{p.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Tabs defaultValue="curl" className="mb-2 text-[0.82rem]">
        <TabsList>
          <TabsTrigger value="curl">curl</TabsTrigger>
          <TabsTrigger value="response">Exemple de réponse</TabsTrigger>
        </TabsList>
        <TabsContent value="curl">
          <div className="relative rounded-md bg-[#1e1e1e] px-3.5 py-3">
            <CopyButton text={curlExample} />
            <pre className="m-0 overflow-x-auto whitespace-pre-wrap break-all text-[0.8rem] text-[#d4d4d4]">
              {curlExample}
            </pre>
          </div>
        </TabsContent>
        <TabsContent value="response">
          <div className="relative rounded-md bg-[#1e1e1e] px-3.5 py-3">
            <CopyButton text={responseExample} />
            <pre className="m-0 max-h-[200px] overflow-x-auto text-[0.8rem] text-[#9cdcfe]">
              {responseExample}
            </pre>
          </div>
        </TabsContent>
      </Tabs>
    </CardContent>
  </Card>
);

// ── Data ──────────────────────────────────────────────────────────────────────

const ENDPOINTS: EndpointProps[] = [
  {
    method: 'GET',
    path: '/api/v1/methods',
    summary: 'Lister les méthodes de vote',
    description:
      'Retourne le catalogue complet des 16+ méthodes de vote supportées par le moteur Vote Lab, avec leur famille et référence académique.',
    params: [
      {
        name: 'family',
        type: 'string',
        range: 'ranked | score | intensity',
        desc: 'Filtrer par famille de méthode',
        default: '(toutes)',
      },
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
    description:
      'Exécute une simulation multi-méthodes sur une population synthétique générée par le modèle spatial de Vote Lab. Les utilités sont calculées sur 20 enjeux politiques.',
    rateLimit: '10 req/min par IP',
    params: [
      {
        name: 'num_candidates',
        type: 'int',
        range: '2–8',
        desc: 'Nombre de candidats',
        default: '4',
      },
      {
        name: 'num_voters',
        type: 'int',
        range: '50–2000',
        desc: "Nombre d'électeurs",
        default: '500',
      },
      {
        name: 'methods',
        type: 'array|string',
        range: '"all" ou liste de clés',
        desc: 'Méthodes à simuler',
        default: '"all"',
      },
      {
        name: 'ideology_distribution',
        type: 'string',
        range: 'random|centrist|polarized|left_skewed|right_skewed',
        desc: 'Distribution idéologique',
        default: '"random"',
      },
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
    description:
      "Comme /simulate mais avec une règle constitutionnelle de vote blanc optionnelle. Retourne l'impact de la règle sur chaque méthode.",
    rateLimit: '5 req/min par IP',
    params: [
      {
        name: 'num_candidates',
        type: 'int',
        range: '2–8',
        desc: 'Nombre de candidats',
        default: '4',
      },
      {
        name: 'num_voters',
        type: 'int',
        range: '50–2000',
        desc: "Nombre d'électeurs",
        default: '500',
      },
      {
        name: 'blank_rule',
        type: 'string',
        range: 'symbolic|competitive|threshold_30|majority_required',
        desc: 'Règle du vote blanc (optionnelle)',
        default: '(désactivé)',
      },
      {
        name: 'methods',
        type: 'array|string',
        range: '"all" ou liste',
        desc: 'Méthodes',
        default: '"all"',
      },
      {
        name: 'ideology_distribution',
        type: 'string',
        range: 'random|centrist|polarized|…',
        desc: 'Distribution idéologique',
        default: '"random"',
      },
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
    description:
      'Retourne les métadonnées des élections réelles incluses dans Vote Lab : France 2002/2022, USA 1992, UK 2015, etc., avec le taux de vote blanc estimé.',
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
    description:
      "Public REST API for integrating Vote Lab's voting simulation engine into research projects.",
  });

  return (
    <div data-style="tailwind" className="mx-auto w-full max-w-[960px] px-3 py-6">
      {/* Header */}
      <div className="mb-4 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="mb-1 text-[1.5rem] font-bold">🔌 API Publique — Vote Lab</h2>
          <p className="mb-0 text-[0.9rem] text-muted-foreground">
            Intégrez le moteur de simulation électorale de Vote Lab dans vos projets de recherche.
            Aucune authentification requise.
          </p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline-secondary" size="sm">
            <a href={`${API_BASE}/api/v1/openapi.json`} target="_blank" rel="noopener noreferrer">
              📄 openapi.json
            </a>
          </Button>
        </div>
      </div>

      {/* Base URL */}
      <Alert variant="secondary" className="mb-6 py-2">
        <strong>Base URL :</strong> <code>{API_BASE}/api/v1</code>
        {' · '}
        <span className="text-muted-foreground">Toutes les réponses sont en JSON · UTF-8</span>
      </Alert>

      {/* Rate limits info */}
      <Card className="mb-6 border-[#ffc107]">
        <CardContent className="p-6 py-2">
          <div className="flex flex-wrap gap-4 text-[0.85rem]">
            <span>
              ⏱ <strong>POST /simulate</strong> : 10 requêtes/min par IP
            </span>
            <span>
              ⏱ <strong>POST /compare</strong> : 5 requêtes/min par IP
            </span>
            <span>✓ GET endpoints : illimités</span>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="endpoints" className="mb-6">
        <TabsList className="h-auto flex-wrap justify-start">
          <TabsTrigger value="endpoints">📍 Endpoints</TabsTrigger>
          <TabsTrigger value="examples">💻 Exemples de code</TabsTrigger>
          <TabsTrigger value="usecases">🎓 Cas d'usage</TabsTrigger>
        </TabsList>

        {/* Endpoints tab */}
        <TabsContent value="endpoints">
          {ENDPOINTS.map((ep) => (
            <EndpointCard key={ep.path} {...ep} />
          ))}
        </TabsContent>

        {/* Code examples tab */}
        <TabsContent value="examples">
          <div className="grid grid-cols-1 gap-4">
            {USE_CASES.map((uc) => (
              <Card key={uc.title}>
                <CardHeader className="p-6 py-3 font-semibold">
                  {uc.icon} {uc.title}
                </CardHeader>
                <CardContent className="p-0">
                  <div className="relative">
                    <CopyButton text={uc.code} />
                    <pre className="m-0 overflow-x-auto rounded-b-lg bg-[#1e1e1e] px-3.5 py-4 text-[0.8rem] text-[#9cdcfe]">
                      {uc.code}
                    </pre>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Use cases tab */}
        <TabsContent value="usecases">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {[
              {
                title: 'Comparaison systématique',
                desc: "Simulez la même élection sous 16 méthodes et comparez les vainqueurs pour illustrer le théorème d'impossibilité d'Arrow dans vos cours ou publications.",
              },
              {
                title: 'Analyse Monte Carlo',
                desc: "Répétez 1 000 simulations avec différentes distributions idéologiques et calculez la robustesse de chaque méthode à la variance de l'électorat.",
              },
              {
                title: 'Étude du vote blanc',
                desc: "Utilisez /compare avec blank_rule=threshold_30 pour modéliser l'impact de la règle colombienne (> 50% → nouvelle élection) sur différentes configurations.",
              },
              {
                title: 'Dataset pour ML',
                desc: 'Générez des milliers de simulations avec graine fixe pour entraîner des modèles prédictifs sur les comportements des méthodes de vote.',
              },
              {
                title: 'Enseignement interactif',
                desc: 'Intégrez Vote Lab dans un notebook Jupyter ou une app Shiny pour montrer en temps réel comment le résultat change selon la méthode choisie.',
              },
              {
                title: 'Réplication de résultats',
                desc: 'Utilisez ideology_distribution=polarized pour reproduire des scénarios proches des élections de 2002 en France ou 1992 aux USA.',
              },
            ].map(({ title, desc }) => (
              <Card className="h-full" key={title}>
                <CardContent className="p-6">
                  <h6 className="font-bold">{title}</h6>
                  <p className="mb-0 text-[0.85rem] text-muted-foreground">{desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Footer */}
      <div className="mt-6 text-center text-[0.78rem] text-muted-foreground">
        Vote Lab est open-source · Licence MIT ·{' '}
        <a href="https://github.com/Burbanit0/Vote-App" target="_blank" rel="noopener noreferrer">
          GitHub
        </a>
        {' · '}
        <a href={`${API_BASE}/api/v1/openapi.json`} target="_blank" rel="noopener noreferrer">
          OpenAPI 3.0
        </a>
      </div>
    </div>
  );
};

export default ApiDocsPage;
