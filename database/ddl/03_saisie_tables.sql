-- ═══════════════════════════════════════════════════════════════
-- SCHÉMA APP_STAGING — Lots et Données Saisies (Normalisé 3NF)
-- ═══════════════════════════════════════════════════════════════

-- ─── 1. Table LOT DE SAISIE (L'enveloppe globale) ───
DROP TABLE IF EXISTS app_staging.lot_saisie CASCADE;
CREATE TABLE app_staging.lot_saisie (
    id_lot              BIGSERIAL PRIMARY KEY,
    id_centre           INTEGER NOT NULL REFERENCES app_staging.ref_centre(id_centre),
    id_periode          INTEGER NOT NULL REFERENCES app_staging.ref_periode(id_periode),
    type_donnees        VARCHAR(30) NOT NULL CHECK (type_donnees IN ('indicateurs', 'reclamations')),
    statut_agrege       VARCHAR(50) DEFAULT 'brouillon',
    cree_par            INTEGER NOT NULL REFERENCES app_auth.utilisateurs(id_utilisateur),
    date_creation       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    date_soumission     TIMESTAMP,
    CONSTRAINT uq_lot_unique UNIQUE (id_centre, id_periode, type_donnees)
);

-- ─── 2. Table PIVOT DONNÉE SAISIE (Ligne par ligne) ───
DROP TABLE IF EXISTS app_staging.donnee_saisie CASCADE;
CREATE TABLE app_staging.donnee_saisie (
    id_donnee           BIGSERIAL PRIMARY KEY,
    id_lot              BIGINT NOT NULL REFERENCES app_staging.lot_saisie(id_lot) ON DELETE CASCADE,
    type_donnee         VARCHAR(30) NOT NULL CHECK (type_donnee IN ('indicateur', 'reclamation')),
    statut              VARCHAR(30) DEFAULT 'brouillon' 
                        CHECK (statut IN ('brouillon', 'soumis', 'valide_dp', 'rejete_dp', 'valide_regional', 'rejete_regional')),
    date_modification   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─── 3. Table Fille : SAISIE INDICATEUR ───
DROP TABLE IF EXISTS app_staging.saisie_indicateur CASCADE;
CREATE TABLE app_staging.saisie_indicateur (
    id_donnee           BIGINT PRIMARY KEY REFERENCES app_staging.donnee_saisie(id_donnee) ON DELETE CASCADE,
    id_type_indicateur  INTEGER NOT NULL REFERENCES app_staging.ref_type_indicateur(id_type_indicateur),
    valeur_indicateur   DOUBLE PRECISION NOT NULL
);

-- ─── 4. Table Fille : SAISIE RÉCLAMATION (Standard, y compris AUTRES avec commentaire) ───
DROP TABLE IF EXISTS app_staging.saisie_reclamation CASCADE;
CREATE TABLE app_staging.saisie_reclamation (
    id_donnee                BIGINT PRIMARY KEY REFERENCES app_staging.donnee_saisie(id_donnee) ON DELETE CASCADE,
    id_type_reclamation      INTEGER NOT NULL REFERENCES app_staging.ref_type_reclamation(id_type_reclamation),
    nombre_reclamations      INTEGER DEFAULT 0,
    temps_moyen_coupure_h    DOUBLE PRECISION DEFAULT 0,
    delai_moyen_traitement_j DOUBLE PRECISION DEFAULT 0,
    valeur_brute             DOUBLE PRECISION DEFAULT 0,
    commentaire_autre        TEXT
);

COMMENT ON COLUMN app_staging.saisie_reclamation.commentaire_autre IS
    'Commentaire optionnel lorsque le type = AUTRES';

-- ─── Index de performance ───
CREATE INDEX idx_lot_centre ON app_staging.lot_saisie(id_centre);
CREATE INDEX idx_lot_periode ON app_staging.lot_saisie(id_periode);
CREATE INDEX idx_lot_statut ON app_staging.lot_saisie(statut_agrege);
CREATE INDEX idx_donnee_lot ON app_staging.donnee_saisie(id_lot);
CREATE INDEX idx_donnee_statut ON app_staging.donnee_saisie(statut);