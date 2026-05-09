import React from 'react';
import { Card, Col, Row } from 'react-bootstrap';

export type BlankRule = 'symbolic' | 'competitive' | 'threshold_30' | 'majority_required';

interface RuleDef {
  label: string;
  emoji: string;
  desc: string;
  consequence: string;
  color: string;
}

const RULES: Record<BlankRule, RuleDef> = {
  symbolic: {
    label: 'Symbolique',
    emoji: '📊',
    color: '#6c757d',
    desc: 'Droit actuel français (article L66 du Code électoral)',
    consequence:
      'Le vote blanc est compté dans les suffrages exprimés, mais ne peut pas faire gagner une élection. Le candidat en tête parmi les candidats réels est élu.',
  },
  competitive: {
    label: 'Compétitif',
    emoji: '⚔️',
    color: '#e15759',
    desc: 'Le vote blanc est un candidat à part entière',
    consequence:
      "Si le vote blanc obtient le plus de voix (pluralité) ou gagne le dernier tour (IRV), l'élection est en crise constitutionnelle : aucun candidat n'est légitime.",
  },
  threshold_30: {
    label: 'Seuil 30%',
    emoji: '🚨',
    color: '#f28e2b',
    desc: 'Une forte contestation invalide l\'élection',
    consequence:
      "Si plus de 30% des votants choisissent le vote blanc, l'élection est déclarée nulle et de nouvelles candidatures doivent être présentées.",
  },
  majority_required: {
    label: 'Majorité requise',
    emoji: '⚖️',
    color: '#4e79a7',
    desc: 'Le vainqueur doit battre le blanc en duel direct',
    consequence:
      "Si une majorité de votants préfère le vote blanc au candidat déclaré vainqueur, le mandat est contesté. Cette règle renforce la légitimité de l'élu.",
  },
};

interface Props {
  selected: BlankRule;
  onChange: (rule: BlankRule) => void;
  hasBlankCandidate: boolean;
}

const BlankVoteRuleSelector: React.FC<Props> = ({ selected, onChange, hasBlankCandidate }) => (
  <div>
    <p className="text-muted small mb-1">
      Choisissez le cadre constitutionnel qui régit le vote blanc dans ce scénario.
    </p>
    {!hasBlankCandidate && (
      <div className="alert alert-warning py-2 mb-3" style={{ fontSize: '0.85rem' }}>
        ⚠️ Vous n'avez pas ajouté le Vote Blanc à l'étape 1. Les résultats "avec vote blanc" se baseront sur les seuils d'insatisfaction des électeurs, pas sur un candidat explicite.
      </div>
    )}

    <Row className="g-3">
      {(Object.entries(RULES) as [BlankRule, RuleDef][]).map(([key, rule]) => {
        const isSelected = selected === key;
        return (
          <Col md={6} key={key}>
            <Card
              className="h-100"
              style={{
                cursor: 'pointer',
                borderColor: isSelected ? rule.color : undefined,
                borderWidth: isSelected ? 2 : 1,
                transition: 'border-color 0.15s',
              }}
              onClick={() => onChange(key)}
            >
              <Card.Body>
                <div className="d-flex align-items-center gap-2 mb-2">
                  <span style={{ fontSize: '1.4rem' }}>{rule.emoji}</span>
                  <div>
                    <div className="fw-bold" style={{ color: isSelected ? rule.color : undefined }}>
                      {rule.label}
                    </div>
                    <small className="text-muted">{rule.desc}</small>
                  </div>
                  {isSelected && (
                    <span className="ms-auto" style={{ color: rule.color, fontSize: '1.2rem' }}>✓</span>
                  )}
                </div>
                <p className="text-muted mb-0" style={{ fontSize: '0.82rem', lineHeight: 1.5 }}>
                  {rule.consequence}
                </p>
              </Card.Body>
            </Card>
          </Col>
        );
      })}
    </Row>

    <div className="mt-4 p-3 rounded" style={{ backgroundColor: '#f8f9fa', fontSize: '0.85rem' }}>
      <strong>Règle sélectionnée : {RULES[selected].emoji} {RULES[selected].label}</strong>
      <p className="mb-0 mt-1 text-muted">{RULES[selected].consequence}</p>
    </div>
  </div>
);

export default BlankVoteRuleSelector;
