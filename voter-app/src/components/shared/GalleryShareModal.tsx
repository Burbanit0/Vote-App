import React, { useState } from 'react';
import { Alert, Badge, Button, Form, Modal, Spinner } from 'react-bootstrap';
import { galleryApi } from '../../services/galleryApi';

const SUGGESTED_TAGS = [
  'paradoxe', 'condorcet', 'vote-blanc', 'borda', 'schulze', 'irv',
  'plurality', 'fragmentation', 'vote-utile', 'star', 'score',
  'polarisation', 'consensus', 'crise-constitutionnelle',
];

interface Props {
  show: boolean;
  onHide: () => void;
  params?: Record<string, unknown>;
  resultsSummary?: Record<string, unknown>;
  suggestedTags?: string[];
}

const GalleryShareModal: React.FC<Props> = ({
  show, onHide, params = {}, resultsSummary = {}, suggestedTags = [],
}) => {
  const [title,   setTitle]   = useState('');
  const [desc,    setDesc]    = useState('');
  const [tags,    setTags]    = useState<string[]>(suggestedTags.slice(0, 3));
  const [saving,  setSaving]  = useState(false);
  const [success, setSuccess] = useState(false);
  const [error,   setError]   = useState<string | null>(null);

  const toggleTag = (tag: string) => {
    setTags((prev) =>
      prev.includes(tag) ? prev.filter((t) => t !== tag) : [...prev, tag].slice(0, 10),
    );
  };

  const handleSubmit = async () => {
    if (!title.trim()) { setError('Le titre est requis.'); return; }
    if (!desc.trim())  { setError('La description est requise.'); return; }
    setSaving(true);
    setError(null);
    try {
      await galleryApi.create({
        title:           title.trim(),
        description:     desc.trim(),
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
    setTitle(''); setDesc(''); setTags(suggestedTags.slice(0, 3));
    setSuccess(false); setError(null);
    onHide();
  };

  return (
    <Modal show={show} onHide={handleHide} centered>
      <Modal.Header closeButton>
        <Modal.Title>💾 Partager dans la galerie</Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {success ? (
          <Alert variant="success">
            ✓ Votre scénario a été publié dans la{' '}
            <a href="/galerie">galerie publique</a> !
          </Alert>
        ) : (
          <>
            {error && <Alert variant="danger" className="py-2">{error}</Alert>}
            <Form.Group className="mb-3">
              <Form.Label htmlFor="gsh-title" className="fw-semibold">Titre *</Form.Label>
              <Form.Control
                id="gsh-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ex : Le paradoxe de Condorcet illustré"
                maxLength={200}
              />
            </Form.Group>
            <Form.Group className="mb-3">
              <Form.Label htmlFor="gsh-desc" className="fw-semibold">Description *</Form.Label>
              <Form.Control
                id="gsh-desc"
                as="textarea"
                rows={3}
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="Décrivez ce qui rend ce scénario intéressant…"
              />
            </Form.Group>
            <Form.Group>
              <Form.Label className="fw-semibold">
                Tags{' '}
                <span className="text-muted fw-normal small">({tags.length}/10)</span>
              </Form.Label>
              <div className="d-flex flex-wrap gap-1 mt-1">
                {SUGGESTED_TAGS.map((tag) => (
                  <Badge
                    key={tag}
                    bg={tags.includes(tag) ? 'primary' : 'secondary'}
                    style={{ cursor: 'pointer', fontSize: '0.78rem', padding: '4px 8px' }}
                    onClick={() => toggleTag(tag)}
                    role="checkbox"
                    aria-checked={tags.includes(tag)}
                    aria-label={`Tag: ${tag}`}
                  >
                    {tag}
                  </Badge>
                ))}
              </div>
              <Form.Text muted>Cliquer pour activer / désactiver</Form.Text>
            </Form.Group>
          </>
        )}
      </Modal.Body>
      <Modal.Footer>
        <Button variant="secondary" onClick={handleHide}>Fermer</Button>
        {!success && (
          <Button variant="success" onClick={handleSubmit} disabled={saving}>
            {saving ? <><Spinner size="sm" className="me-1" />Publication…</> : '🚀 Publier'}
          </Button>
        )}
      </Modal.Footer>
    </Modal>
  );
};

export default GalleryShareModal;
