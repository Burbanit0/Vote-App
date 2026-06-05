import React, { useMemo } from 'react';
import { Card, CardBody } from '@/components/ui/card';
import { Col, Row } from '@/components/ui/grid';
import { useTranslation } from 'react-i18next';

export type BlankRule = 'symbolic' | 'competitive' | 'threshold_30' | 'majority_required';

interface RuleDef {
  label: string;
  emoji: string;
  desc: string;
  consequence: string;
  color: string;
}

interface Props {
  selected: BlankRule;
  onChange: (rule: BlankRule) => void;
  hasBlankCandidate: boolean;
}

const BlankVoteRuleSelector: React.FC<Props> = ({ selected, onChange, hasBlankCandidate }) => {
  const { t } = useTranslation();

  const RULES: Record<BlankRule, RuleDef> = useMemo(
    () => ({
      symbolic: {
        label: t('scenario.rule.symbolic.label'),
        emoji: '📊',
        color: '#6c757d',
        desc: t('scenario.rule.symbolic.desc'),
        consequence: t('scenario.rule.symbolic.consequence'),
      },
      competitive: {
        label: t('scenario.rule.competitive.label'),
        emoji: '⚔️',
        color: '#e15759',
        desc: t('scenario.rule.competitive.desc'),
        consequence: t('scenario.rule.competitive.consequence'),
      },
      threshold_30: {
        label: t('scenario.rule.threshold_30.label'),
        emoji: '🚨',
        color: '#f28e2b',
        desc: t('scenario.rule.threshold_30.desc'),
        consequence: t('scenario.rule.threshold_30.consequence'),
      },
      majority_required: {
        label: t('scenario.rule.majority_required.label'),
        emoji: '⚖️',
        color: '#4e79a7',
        desc: t('scenario.rule.majority_required.desc'),
        consequence: t('scenario.rule.majority_required.consequence'),
      },
    }),
    [t]
  );

  return (
    <div>
      <p className="text-muted-foreground text-sm mb-1">{t('scenario.ruleIntro')}</p>
      {!hasBlankCandidate && (
        <div className="alert alert-warning py-2 mb-3" style={{ fontSize: '0.85rem' }}>
          {t('scenario.ruleNoBlankWarning')}
        </div>
      )}

      <Row className="g-3">
        {(Object.entries(RULES) as [BlankRule, RuleDef][]).map(([key, rule]) => {
          const isSelected = selected === key;
          return (
            <Col md={6} key={key}>
              <Card
                className="h-full"
                style={{
                  cursor: 'pointer',
                  borderColor: isSelected ? rule.color : undefined,
                  borderWidth: isSelected ? 2 : 1,
                  transition: 'border-color 0.15s',
                }}
                onClick={() => onChange(key)}
              >
                <CardBody>
                  <div className="flex items-center gap-2 mb-2">
                    <span style={{ fontSize: '1.4rem' }}>{rule.emoji}</span>
                    <div>
                      <div
                        className="font-bold"
                        style={{ color: isSelected ? rule.color : undefined }}
                      >
                        {rule.label}
                      </div>
                      <small className="text-muted-foreground">{rule.desc}</small>
                    </div>
                    {isSelected && (
                      <span className="ml-auto" style={{ color: rule.color, fontSize: '1.2rem' }}>
                        ✓
                      </span>
                    )}
                  </div>
                  <p
                    className="text-muted-foreground mb-0"
                    style={{ fontSize: '0.82rem', lineHeight: 1.5 }}
                  >
                    {rule.consequence}
                  </p>
                </CardBody>
              </Card>
            </Col>
          );
        })}
      </Row>

      <div className="mt-4 p-3 rounded" style={{ backgroundColor: '#f8f9fa', fontSize: '0.85rem' }}>
        <strong>
          {t('scenario.ruleSummary', {
            emoji: RULES[selected].emoji,
            label: RULES[selected].label,
          })}
        </strong>
        <p className="mb-0 mt-1 text-muted-foreground">{RULES[selected].consequence}</p>
      </div>
    </div>
  );
};

export default BlankVoteRuleSelector;
