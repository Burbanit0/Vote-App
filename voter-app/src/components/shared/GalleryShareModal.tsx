import React, { useState } from 'react';
import { galleryApi } from '../../services/galleryApi';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Spinner } from '@/components/ui/spinner';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

const SUGGESTED_TAGS = [
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

interface Props {
  show: boolean;
  onHide: () => void;
  params?: Record<string, unknown>;
  resultsSummary?: Record<string, unknown>;
  suggestedTags?: string[];
}

const GalleryShareModal: React.FC<Props> = ({
  show,
  onHide,
  params = {},
  resultsSummary = {},
  suggestedTags = [],
}) => {
  const [title, setTitle] = useState('');
  const [desc, setDesc] = useState('');
  const [tags, setTags] = useState<string[]>(suggestedTags.slice(0, 3));
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag].slice(0, 10)
    );
  };

  const handleSubmit = async () => {
    if (!title.trim()) {
      setError('Le titre est requis.');
      return;
    }
    if (!desc.trim()) {
      setError('La description est requise.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await galleryApi.create({
        title: title.trim(),
        description: desc.trim(),
        params,
        results_summary: resultsSummary,
        tags,
      });
      setSuccess(true);
    } catch (e: any) {
      setError(e?.response?.data?.error ?? 'Erreur lors de la publication.');
    } finally {
      setSaving(false);
    }
  };

  const handleHide = () => {
    setTitle('');
    setDesc('');
    setTags(suggestedTags.slice(0, 3));
    setSuccess(false);
    setError(null);
    onHide();
  };

  return (
    <Dialog
      open={show}
      onOpenChange={(o) => {
        if (!o) handleHide();
      }}
    >
      <DialogContent data-style="tailwind">
        <DialogHeader>
          <DialogTitle>💾 Partager dans la galerie</DialogTitle>
        </DialogHeader>

        <div>
          {success ? (
            <Alert variant="success">
              ✓ Votre scénario a été publié dans la <a href="/galerie">galerie publique</a> !
            </Alert>
          ) : (
            <>
              {error && (
                <Alert variant="danger" className="mb-3 py-2">
                  {error}
                </Alert>
              )}
              <div className="mb-3 space-y-1.5">
                <Label htmlFor="gsh-title" className="font-semibold">
                  Titre *
                </Label>
                <Input
                  id="gsh-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Ex : Le paradoxe de Condorcet illustré"
                  maxLength={200}
                />
              </div>
              <div className="mb-3 space-y-1.5">
                <Label htmlFor="gsh-desc" className="font-semibold">
                  Description *
                </Label>
                <textarea
                  id="gsh-desc"
                  rows={3}
                  value={desc}
                  onChange={(e) => setDesc(e.target.value)}
                  placeholder="Décrivez ce qui rend ce scénario intéressant…"
                  className="flex w-full rounded-md border border-border border-input bg-transparent px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                />
              </div>
              <div>
                <Label className="font-semibold">
                  Tags{' '}
                  <span className="text-sm font-normal text-muted-foreground">
                    ({tags.length}/10)
                  </span>
                </Label>
                <div className="mt-1 flex flex-wrap gap-1">
                  {SUGGESTED_TAGS.map((tag) => (
                    <Badge
                      key={tag}
                      variant={tags.includes(tag) ? 'primary' : 'secondary'}
                      className="cursor-pointer px-2 py-1 text-[0.78rem]"
                      onClick={() => toggleTag(tag)}
                      role="checkbox"
                      aria-checked={tags.includes(tag)}
                      aria-label={`Tag: ${tag}`}
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
                <small className="text-muted-foreground">Cliquer pour activer / désactiver</small>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="secondary" onClick={handleHide}>
            Fermer
          </Button>
          {!success && (
            <Button variant="success" onClick={handleSubmit} disabled={saving}>
              {saving ? (
                <>
                  <Spinner size="sm" className="mr-1" />
                  Publication…
                </>
              ) : (
                '🚀 Publier'
              )}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default GalleryShareModal;
