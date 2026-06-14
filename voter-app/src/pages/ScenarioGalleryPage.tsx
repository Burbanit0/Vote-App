import React, { useCallback, useEffect, useState } from 'react';
import { useMetaTags } from '../hooks/useMetaTags';
import { galleryApi, GalleryScenario } from '../services/galleryApi';
import GalleryShareModal from '../components/shared/GalleryShareModal';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Spinner } from '@/components/ui/spinner';

// ── Tailwind-migrated (Phase 6) ──────────────────────────────────────────────

const TAG_COLORS: Record<string, string> = {
  paradoxe: '#b71c1c',
  condorcet: '#1a56cc',
  'vote-blanc': '#006957',
  borda: '#b35c00',
  schulze: '#544200',
  irv: '#1b5e20',
  plurality: '#6c757d',
  fragmentation: '#7c3aed',
  'vote-utile': '#b35c00',
  star: '#006957',
  score: '#1a56cc',
  polarisation: '#b71c1c',
  consensus: '#1b5e20',
  'crise-constitutionnelle': '#b71c1c',
};

function tagColor(tag: string): string {
  return TAG_COLORS[tag] ?? '#495057';
}

// A tag chip with an arbitrary background colour.
const TagChip: React.FC<React.HTMLAttributes<HTMLSpanElement> & { color?: string }> = ({
  color,
  className,
  style,
  ...props
}) => (
  <span
    className={`inline-flex items-center rounded-md px-[7px] py-[3px] text-[0.7rem] font-semibold text-white ${className ?? ''}`}
    style={{ background: color, ...style }}
    {...props}
  />
);

// ── ScenarioCard ──────────────────────────────────────────────────────────────

const ScenarioCard: React.FC<{ scenario: GalleryScenario; onExplore: () => void }> = ({
  scenario,
  onExplore,
}) => (
  <Card className="h-full shadow-sm transition-transform hover:-translate-y-0.5">
    <CardContent className="flex flex-1 flex-col p-6">
      <CardTitle className="mb-2 text-base leading-snug">{scenario.title}</CardTitle>
      <p className="line-clamp-3 flex-grow text-[0.85rem] leading-normal text-muted-foreground">
        {scenario.description}
      </p>
      <div className="my-2 flex flex-wrap gap-1">
        {scenario.tags.slice(0, 4).map((tag) => (
          <TagChip key={tag} color={tagColor(tag)}>
            {tag}
          </TagChip>
        ))}
        {scenario.tags.length > 4 && (
          <Badge variant="secondary" className="px-[7px] py-[3px] text-[0.7rem]">
            +{scenario.tags.length - 4}
          </Badge>
        )}
      </div>
    </CardContent>
    <CardFooter className="flex items-center justify-between border-t border-border bg-transparent p-6 py-2">
      <small className="text-muted-foreground">👁 {scenario.views.toLocaleString()} vues</small>
      <Button variant="outline-primary" size="sm" onClick={onExplore}>
        Explorer →
      </Button>
    </CardFooter>
  </Card>
);

// ── ScenarioGalleryPage ───────────────────────────────────────────────────────

const ALL_TAGS = [
  'paradoxe',
  'condorcet',
  'vote-blanc',
  'borda',
  'schulze',
  'irv',
  'plurality',
  'fragmentation',
  'vote-utile',
  'star',
  'score',
  'polarisation',
  'consensus',
  'crise-constitutionnelle',
];

const ScenarioGalleryPage: React.FC = () => {
  useMetaTags({
    title: 'Galerie de scénarios — Vote Lab',
    description:
      '6 scénarios électoraux pédagogiques à explorer : paradoxe de Condorcet, vote blanc, effet spoiler…',
  });

  const [featured, setFeatured] = useState<GalleryScenario[]>([]);
  const [items, setItems] = useState<GalleryScenario[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [sort, setSort] = useState('recent');
  const [activeTag, setActiveTag] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showShare, setShowShare] = useState(false);
  const [detailId, setDetailId] = useState<number | null>(null);
  const [detailData, setDetailData] = useState<GalleryScenario | null>(null);

  useEffect(() => {
    galleryApi
      .featured()
      .then(setFeatured)
      .catch(() => {});
  }, []);

  const fetchItems = useCallback(
    async (p = 1, s = sort, t = activeTag) => {
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
    },
    [sort, activeTag]
  );

  useEffect(() => {
    fetchItems(1, sort, activeTag);
  }, [sort, activeTag]); // eslint-disable-line

  useEffect(() => {
    if (!detailId) return;
    galleryApi
      .get(detailId)
      .then(setDetailData)
      .catch(() => setDetailData(null));
  }, [detailId]);

  const handleTagClick = (tag: string) => {
    setActiveTag((prev) => (prev === tag ? '' : tag));
    setPage(1);
  };

  const handleExplore = (id: number) => setDetailId(id);

  const gridCols = 'grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3';

  return (
    <div data-style="tailwind" className="mx-auto w-full max-w-[1200px] px-3 py-6">
      {/* Header */}
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="mb-1 text-[1.5rem] font-bold">🗃 Galerie de scénarios</h2>
          <p className="mb-0 text-[0.9rem] text-muted-foreground">
            {total > 0
              ? `${total} scénarios électoraux à explorer.`
              : 'Scénarios électoraux pédagogiques.'}{' '}
            <span className="text-muted-foreground">Simulez, comparez, partagez.</span>
          </p>
        </div>
        <Button variant="success" onClick={() => setShowShare(true)}>
          💾 Proposer un scénario
        </Button>
      </div>

      {error && (
        <Alert variant="warning" className="mb-4">
          {error}
        </Alert>
      )}

      {/* Featured section */}
      {featured.length > 0 && (
        <div className="mb-6 rounded-lg bg-muted p-4">
          <h5 className="mb-4 text-lg font-bold">⭐ En vedette</h5>
          <div className={gridCols}>
            {featured.map((s) => (
              <ScenarioCard key={s.id} scenario={s} onExplore={() => handleExplore(s.id)} />
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        {/* Sort */}
        <div className="flex gap-1" role="group" aria-label="Trier par">
          {[
            { key: 'recent', label: 'Récents' },
            { key: 'popular', label: 'Populaires' },
            { key: 'featured', label: 'En vedette' },
          ].map(({ key, label }) => (
            <Button
              key={key}
              size="sm"
              variant={sort === key ? 'primary' : 'outline-secondary'}
              onClick={() => {
                setSort(key);
                setPage(1);
              }}
              aria-pressed={sort === key}
            >
              {label}
            </Button>
          ))}
        </div>

        {/* Tag filter */}
        <div className="flex flex-wrap gap-1" role="group" aria-label="Filtrer par tag">
          {activeTag && (
            <Badge
              variant="secondary"
              className="cursor-pointer px-2 py-1 text-[0.78rem]"
              onClick={() => {
                setActiveTag('');
                setPage(1);
              }}
            >
              ✕ {activeTag}
            </Badge>
          )}
          {ALL_TAGS.filter((t) => t !== activeTag)
            .slice(0, 8)
            .map((tag) => (
              <TagChip
                key={tag}
                color={tagColor(tag)}
                className="cursor-pointer text-[0.72rem] opacity-75"
                onClick={() => handleTagClick(tag)}
                role="button"
                aria-label={`Filtrer : ${tag}`}
              >
                {tag}
              </TagChip>
            ))}
        </div>
      </div>

      {/* Main grid */}
      {loading ? (
        <div className="py-12 text-center">
          <Spinner />
          <div className="mt-2 text-muted-foreground">Chargement…</div>
        </div>
      ) : items.length === 0 ? (
        <Alert variant="info">
          Aucun scénario trouvé{activeTag ? ` avec le tag « ${activeTag} »` : ''}.
        </Alert>
      ) : (
        <div className={gridCols}>
          {items.map((s) => (
            <ScenarioCard key={s.id} scenario={s} onExplore={() => handleExplore(s.id)} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {pages > 1 && (
        <div className="mt-6 flex justify-center gap-2">
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => fetchItems(page - 1, sort, activeTag)}
            disabled={page <= 1}
          >
            ← Précédente
          </Button>
          <span className="self-center text-sm text-muted-foreground">
            Page {page} / {pages}
          </span>
          <Button
            variant="outline-secondary"
            size="sm"
            onClick={() => fetchItems(page + 1, sort, activeTag)}
            disabled={page >= pages}
          >
            Suivante →
          </Button>
        </div>
      )}

      {/* Detail modal */}
      {detailId && detailData && (
        <div
          className="fixed inset-0 z-[1050] flex items-center justify-center bg-black/50 p-4"
          onClick={() => {
            setDetailId(null);
            setDetailData(null);
          }}
        >
          <Card className="z-[1051] w-full max-w-[560px]" onClick={(e) => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between p-6 py-3">
              <strong>{detailData.title}</strong>
              <Button
                variant="link"
                size="sm"
                onClick={() => {
                  setDetailId(null);
                  setDetailData(null);
                }}
              >
                ✕
              </Button>
            </CardHeader>
            <CardContent className="p-6">
              <p className="mb-4 text-[0.88rem] text-muted-foreground">{detailData.description}</p>
              {detailData.results_summary && Object.keys(detailData.results_summary).length > 0 && (
                <div className="mb-4">
                  <div className="mb-1 text-sm font-semibold">
                    Résultats (vainqueurs par méthode)
                  </div>
                  {detailData.results_summary.winners && (
                    <div className="flex flex-wrap gap-2">
                      {Object.entries(detailData.results_summary.winners).map(([m, w]) => (
                        <span key={m} className="text-[0.8rem]">
                          <span className="text-muted-foreground">{m}:</span> <strong>{w}</strong>
                        </span>
                      ))}
                    </div>
                  )}
                  {detailData.results_summary.note && (
                    <div className="mt-2 text-[0.8rem] text-muted-foreground">
                      {detailData.results_summary.note}
                    </div>
                  )}
                </div>
              )}
              <div className="flex flex-wrap gap-1">
                {detailData.tags.map((tag) => (
                  <TagChip key={tag} color={tagColor(tag)} className="text-[0.72rem]">
                    {tag}
                  </TagChip>
                ))}
              </div>
            </CardContent>
            <CardFooter className="flex items-center justify-between p-6 py-3">
              <small className="text-muted-foreground">
                👁 {detailData.views.toLocaleString()} vues
              </small>
              <Button asChild variant="primary" size="sm">
                <a
                  href={
                    detailData.params
                      ? `/simulation/compare?candidates=${encodeURIComponent(
                          ((detailData.params.candidates as string[]) || []).join(', ')
                        )}`
                      : '/simulation/compare'
                  }
                >
                  Ouvrir dans le simulateur →
                </a>
              </Button>
            </CardFooter>
          </Card>
        </div>
      )}

      {/* Share modal */}
      <GalleryShareModal show={showShare} onHide={() => setShowShare(false)} />
    </div>
  );
};

export default ScenarioGalleryPage;
