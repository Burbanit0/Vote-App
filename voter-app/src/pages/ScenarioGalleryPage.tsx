import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Alert, Badge, Button, Card, Col, Container, Form, Row, Spinner,
} from 'react-bootstrap';
import { useMetaTags } from '../hooks/useMetaTags';
import { galleryApi, GalleryScenario } from '../services/galleryApi';
import GalleryShareModal from '../components/shared/GalleryShareModal';

// ── Tag colour mapping ────────────────────────────────────────────────────────

const TAG_COLORS: Record<string, string> = {
  paradoxe: '#b71c1c', condorcet: '#1a56cc', 'vote-blanc': '#006957',
  borda: '#b35c00', schulze: '#544200', irv: '#1b5e20', plurality: '#6c757d',
  fragmentation: '#7c3aed', 'vote-utile': '#b35c00', star: '#006957',
  score: '#1a56cc', polarisation: '#b71c1c', consensus: '#1b5e20',
  'crise-constitutionnelle': '#b71c1c',
};

function tagColor(tag: string): string { return TAG_COLORS[tag] ?? '#495057'; }

// ── ScenarioCard ──────────────────────────────────────────────────────────────

const ScenarioCard: React.FC<{ scenario: GalleryScenario; onExplore: () => void }> = ({
  scenario, onExplore,
}) => (
  <Card className="h-100 shadow-sm" style={{ transition: 'transform 0.15s', cursor: 'default' }}
    onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.transform = 'translateY(-2px)'; }}
    onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.transform = ''; }}
  >
    <Card.Body className="d-flex flex-column">
      <Card.Title className="fw-bold mb-2" style={{ fontSize: '1rem', lineHeight: 1.3 }}>
        {scenario.title}
      </Card.Title>
      <Card.Text className="text-muted flex-grow-1"
        style={{ fontSize: '0.85rem', lineHeight: 1.5, display: '-webkit-box',
          WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
        {scenario.description}
      </Card.Text>
      <div className="d-flex flex-wrap gap-1 my-2">
        {scenario.tags.slice(0, 4).map((tag) => (
          <Badge key={tag} style={{ background: tagColor(tag), fontSize: '0.7rem', padding: '3px 7px' }}>
            {tag}
          </Badge>
        ))}
        {scenario.tags.length > 4 && (
          <Badge bg="secondary" style={{ fontSize: '0.7rem', padding: '3px 7px' }}>
            +{scenario.tags.length - 4}
          </Badge>
        )}
      </div>
    </Card.Body>
    <Card.Footer className="d-flex align-items-center justify-content-between py-2"
      style={{ background: 'transparent', borderTop: '1px solid var(--bs-border-color)' }}>
      <small className="text-muted">👁 {scenario.views.toLocaleString()} vues</small>
      <Button variant="outline-primary" size="sm" onClick={onExplore}>
        Explorer →
      </Button>
    </Card.Footer>
  </Card>
);

// ── ScenarioGalleryPage ───────────────────────────────────────────────────────

const ALL_TAGS = [
  'paradoxe', 'condorcet', 'vote-blanc', 'borda', 'schulze', 'irv',
  'plurality', 'fragmentation', 'vote-utile', 'star', 'score',
  'polarisation', 'consensus', 'crise-constitutionnelle',
];

const ScenarioGalleryPage: React.FC = () => {
  useMetaTags({
    title: 'Galerie de scénarios — Vote Lab',
    description: '6 scénarios électoraux pédagogiques à explorer : paradoxe de Condorcet, vote blanc, effet spoiler…',
  });

  const [featured,   setFeatured]   = useState<GalleryScenario[]>([]);
  const [items,      setItems]      = useState<GalleryScenario[]>([]);
  const [total,      setTotal]      = useState(0);
  const [page,       setPage]       = useState(1);
  const [pages,      setPages]      = useState(1);
  const [sort,       setSort]       = useState('recent');
  const [activeTag,  setActiveTag]  = useState('');
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);
  const [showShare,  setShowShare]  = useState(false);
  const [detailId,   setDetailId]   = useState<number | null>(null);
  const [detailData, setDetailData] = useState<GalleryScenario | null>(null);

  // ── Fetch featured ──
  useEffect(() => {
    galleryApi.featured()
      .then(setFeatured)
      .catch(() => {});
  }, []);

  // ── Fetch paged list ──
  const fetchItems = useCallback(async (p = 1, s = sort, t = activeTag) => {
    setLoading(true);
    setError(null);
    try {
      const res = await galleryApi.list({ page: p, per_page: 9, sort: s, tag: t });
      setItems(res.items);
      setTotal(res.total);
      setPage(res.page);
      setPages(res.pages);
    } catch {
      setError('Impossible de charger la galerie. Le backend est-il démarré ?');
    } finally {
      setLoading(false);
    }
  }, [sort, activeTag]);

  useEffect(() => { fetchItems(1, sort, activeTag); }, [sort, activeTag]); // eslint-disable-line

  // ── Detail fetch when exploring ──
  useEffect(() => {
    if (!detailId) return;
    galleryApi.get(detailId).then(setDetailData).catch(() => setDetailData(null));
  }, [detailId]);

  const handleTagClick = (tag: string) => {
    setActiveTag((prev) => (prev === tag ? '' : tag));
    setPage(1);
  };

  const handleExplore = (id: number) => setDetailId(id);

  return (
    <Container className="py-4" style={{ maxWidth: 1200 }}>
      {/* Header */}
      <div className="d-flex align-items-start justify-content-between mb-2 flex-wrap gap-2">
        <div>
          <h2 className="mb-1 fw-bold">🗃 Galerie de scénarios</h2>
          <p className="text-muted mb-0" style={{ fontSize: '0.9rem' }}>
            {total > 0 ? `${total} scénarios électoraux à explorer.` : 'Scénarios électoraux pédagogiques.'}
            {' '}
            <span className="text-muted">Simulez, comparez, partagez.</span>
          </p>
        </div>
        <Button variant="success" onClick={() => setShowShare(true)}>
          💾 Proposer un scénario
        </Button>
      </div>

      {error && <Alert variant="warning" className="mb-3">{error}</Alert>}

      {/* Featured section */}
      {featured.length > 0 && (
        <div className="p-3 mb-4 rounded-3" style={{ background: 'var(--bs-secondary-bg, #f8f9fa)' }}>
          <h5 className="fw-bold mb-3">⭐ En vedette</h5>
          <Row className="g-3">
            {featured.map((s) => (
              <Col key={s.id} xs={12} md={6} lg={4}>
                <ScenarioCard scenario={s} onExplore={() => handleExplore(s.id)} />
              </Col>
            ))}
          </Row>
        </div>
      )}

      {/* Filters */}
      <div className="d-flex align-items-center gap-3 mb-3 flex-wrap">
        {/* Sort */}
        <div className="d-flex gap-1" role="group" aria-label="Trier par">
          {[
            { key: 'recent',   label: 'Récents' },
            { key: 'popular',  label: 'Populaires' },
            { key: 'featured', label: 'En vedette' },
          ].map(({ key, label }) => (
            <Button key={key} size="sm"
              variant={sort === key ? 'primary' : 'outline-secondary'}
              onClick={() => { setSort(key); setPage(1); }}
              aria-pressed={sort === key}
            >
              {label}
            </Button>
          ))}
        </div>

        {/* Tag filter */}
        <div className="d-flex flex-wrap gap-1" role="group" aria-label="Filtrer par tag">
          {activeTag && (
            <Badge
              bg="secondary"
              style={{ cursor: 'pointer', fontSize: '0.78rem', padding: '4px 8px' }}
              onClick={() => { setActiveTag(''); setPage(1); }}
            >
              ✕ {activeTag}
            </Badge>
          )}
          {ALL_TAGS.filter((t) => t !== activeTag).slice(0, 8).map((tag) => (
            <Badge
              key={tag}
              style={{ background: tagColor(tag), cursor: 'pointer', fontSize: '0.72rem', padding: '3px 7px', opacity: 0.75 }}
              onClick={() => handleTagClick(tag)}
              role="button"
              aria-label={`Filtrer : ${tag}`}
            >
              {tag}
            </Badge>
          ))}
        </div>
      </div>

      {/* Main grid */}
      {loading ? (
        <div className="text-center py-5"><Spinner /><div className="mt-2 text-muted">Chargement…</div></div>
      ) : items.length === 0 ? (
        <Alert variant="info">
          Aucun scénario trouvé{activeTag ? ` avec le tag « ${activeTag} »` : ''}.
        </Alert>
      ) : (
        <Row className="g-3">
          {items.map((s) => (
            <Col key={s.id} xs={12} md={6} lg={4}>
              <ScenarioCard scenario={s} onExplore={() => handleExplore(s.id)} />
            </Col>
          ))}
        </Row>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="d-flex justify-content-center gap-2 mt-4">
          <Button variant="outline-secondary" size="sm"
            onClick={() => fetchItems(page - 1, sort, activeTag)}
            disabled={page <= 1}>← Précédente</Button>
          <span className="align-self-center text-muted small">
            Page {page} / {pages}
          </span>
          <Button variant="outline-secondary" size="sm"
            onClick={() => fetchItems(page + 1, sort, activeTag)}
            disabled={page >= pages}>Suivante →</Button>
        </div>
      )}

      {/* Detail modal */}
      {detailId && detailData && (
        <div
          style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1050,
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}
          onClick={() => { setDetailId(null); setDetailData(null); }}
        >
          <Card style={{ maxWidth: 560, width: '100%', zIndex: 1051 }}
            onClick={(e) => e.stopPropagation()}>
            <Card.Header className="d-flex align-items-center justify-content-between">
              <strong>{detailData.title}</strong>
              <Button variant="link" size="sm" onClick={() => { setDetailId(null); setDetailData(null); }}>✕</Button>
            </Card.Header>
            <Card.Body>
              <p className="text-muted mb-3" style={{ fontSize: '0.88rem' }}>{detailData.description}</p>
              {detailData.results_summary && Object.keys(detailData.results_summary).length > 0 && (
                <div className="mb-3">
                  <div className="fw-semibold small mb-1">Résultats (vainqueurs par méthode)</div>
                  {(detailData.results_summary as any).winners && (
                    <div className="d-flex flex-wrap gap-2">
                      {Object.entries((detailData.results_summary as any).winners as Record<string, string>).map(([m, w]) => (
                        <span key={m} style={{ fontSize: '0.8rem' }}>
                          <span className="text-muted">{m}:</span>{' '}
                          <strong>{w}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                  {(detailData.results_summary as any).note && (
                    <div className="text-muted mt-2" style={{ fontSize: '0.8rem' }}>
                      {String((detailData.results_summary as any).note)}
                    </div>
                  )}
                </div>
              )}
              <div className="d-flex flex-wrap gap-1">
                {detailData.tags.map((tag) => (
                  <Badge key={tag} style={{ background: tagColor(tag), fontSize: '0.72rem' }}>{tag}</Badge>
                ))}
              </div>
            </Card.Body>
            <Card.Footer className="d-flex justify-content-between align-items-center">
              <small className="text-muted">👁 {detailData.views.toLocaleString()} vues</small>
              <Button variant="primary" size="sm"
                href={detailData.params
                  ? `/simulation/compare?candidates=${encodeURIComponent(
                      ((detailData.params.candidates as string[]) || []).join(', ')
                    )}`
                  : '/simulation/compare'}>
                Ouvrir dans le simulateur →
              </Button>
            </Card.Footer>
          </Card>
        </div>
      )}

      {/* Share modal */}
      <GalleryShareModal
        show={showShare}
        onHide={() => setShowShare(false)}
      />
    </Container>
  );
};

export default ScenarioGalleryPage;
