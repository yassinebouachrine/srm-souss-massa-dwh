# utils/history_display.py
"""
Historique optimisé : marquage inline dans le tableau des données du lot.
"""

import streamlit as st
import pandas as pd
from db.queries import get_historique_correction_donnee
from utils.helpers import format_datetime


def render_historique_donnee(id_donnee: int, element_libelle: str = ""):
    """
    Affiche l'historique complet d'UNE donnée sélectionnée.
    Appelé quand l'utilisateur coche 'Voir historique' dans le tableau des données.
    """
    historique = get_historique_correction_donnee(id_donnee)

    if not historique:
        st.info(f"Aucun historique disponible pour cette donnée (#{id_donnee}).")
        return

    st.markdown(
        f"<div style='background:#F0F9FF;border-left:3px solid #0EA5E9;"
        f"padding:0.75rem 1rem;border-radius:6px;margin:1rem 0;'>"
        f"<div style='font-size:0.9rem;color:#075985;'>"
        f"<strong>Historique de « {element_libelle} »</strong> "
        f"— {len(historique)} modification(s) enregistrée(s)"
        f"</div></div>",
        unsafe_allow_html=True
    )

    # Regrouper les modifications par événement de correction
    corrections_groupees = {}
    for h in historique:
        key = (h["date_correction"], h["corrige_par_nom"], h.get("motif_rejet") or "—")
        if key not in corrections_groupees:
            corrections_groupees[key] = {
                "date": h["date_correction"],
                "auteur": h["corrige_par_nom"],
                "role": h.get("role_correcteur", "—"),
                "motif_rejet": h.get("motif_rejet") or "—",
                "niveau_rejet": h.get("niveau_rejet", "—"),
                "rejete_par": h.get("rejete_par_nom", "—"),
                "commentaire_correcteur": h.get("commentaire_correcteur"),
                "changements": []
            }
        corrections_groupees[key]["changements"].append({
            "champ": h["champ_lisible"],
            "ancienne": h["ancienne_valeur"],
            "nouvelle": h["nouvelle_valeur"]
        })

    for idx, (_, corr) in enumerate(corrections_groupees.items(), 1):
        niveau_lbl = (
            "Admin DP" if corr["niveau_rejet"] == "dp"
            else "Admin Régional" if corr["niveau_rejet"] == "regional"
            else corr["niveau_rejet"]
        )

        st.markdown(
            f"<div style='background:#FFFFFF;border:1px solid #E5E7EB;border-radius:8px;"
            f"padding:1rem;margin-bottom:0.75rem;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"padding-bottom:0.6rem;margin-bottom:0.75rem;border-bottom:1px solid #F3F4F6;'>"
            f"<div>"
            f"<span style='font-weight:600;color:#111827;'>Correction #{idx}</span> "
            f"<span style='color:#6B7280;font-size:0.82rem;'>— par <strong>{corr['auteur']}</strong> "
            f"({corr['role']})</span>"
            f"</div>"
            f"<div style='font-size:0.78rem;color:#9CA3AF;'>{format_datetime(corr['date'])}</div>"
            f"</div>"
            f"<div style='font-size:0.85rem;color:#374151;margin-bottom:0.6rem;'>"
            f"<strong>Motif du rejet ({niveau_lbl}) :</strong> "
            f"<span style='font-style:italic;color:#6B7280;'>« {corr['motif_rejet']} »</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        if corr.get("commentaire_correcteur"):
            st.markdown(
                f"<div style='font-size:0.82rem;color:#374151;margin-bottom:0.6rem;'>"
                f"<strong>Commentaire du correcteur :</strong> "
                f"<span style='font-style:italic;color:#6B7280;'>« {corr['commentaire_correcteur']} »</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        df_changes = pd.DataFrame([{
            "Champ modifié": c["champ"],
            "Ancienne valeur": c["ancienne"] if c["ancienne"] not in (None, "None", "") else "—",
            "Nouvelle valeur": c["nouvelle"] if c["nouvelle"] not in (None, "None", "") else "—",
        } for c in corr["changements"]])

        st.dataframe(df_changes, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)


def render_data_table_with_history(details: list, id_lot: int, data_type: str, key_prefix: str, 
                                     editable_col: str = None, extra_cols: dict = None):
    """
    Affiche le tableau des données du lot avec :
    - marquage visuel des données modifiées
    - case à cocher pour afficher l'historique de chaque donnée modifiée
    
    Args:
        details: liste des données du lot (get_lot_details_indicateurs/reclamations)
        id_lot: ID du lot
        data_type: "indicateurs" ou "reclamations"
        key_prefix: préfixe unique pour les clés Streamlit
        editable_col: si fourni, la colonne devient éditable (retourne le dataframe édité)
        extra_cols: colonnes additionnelles {nom: valeur_par_defaut}

    Returns:
        edited_df (si editable_col) ou None
    """
    from db.queries import get_ids_donnees_modifiees
    from utils.styles import STATUS_LABELS

    if not details:
        st.info("Aucune donnée dans ce lot.")
        return None

    ids_modifiees = get_ids_donnees_modifiees(id_lot)

    # Construction du dataframe
    if data_type == "indicateurs":
        rows = []
        for d in details:
            modif = d["id_donnee"] in ids_modifiees
            rows.append({
                "🔄": "🔄" if modif else "",
                "ID": d["id_donnee"],
                "Code": d["code_indicateur"],
                "Indicateur": d["libelle_indicateur"],
                "Catégorie": d.get("categorie", "—"),
                "Unité": d.get("unite", "—"),
                "Valeur": d["valeur_indicateur"],
                "Statut": STATUS_LABELS.get(d["statut"], d["statut"]),
                "Voir historique": False,
                "_modifiee": modif,
            })
    else:
        rows = []
        for d in details:
            modif = d["id_donnee"] in ids_modifiees
            if d.get("code_type") == "AUTRES":
                val = str(d.get("commentaire_autre") or "—")
            else:
                v = d.get("valeur_brute", 0)
                val = str(int(v)) if isinstance(v, float) and v == int(v) else str(v)
            rows.append({
                "🔄": "🔄" if modif else "",
                "ID": d["id_donnee"],
                "Code": d["code_type"],
                "Type": d["libelle_reclamation"],
                "Valeur": val,
                "Statut": STATUS_LABELS.get(d["statut"], d["statut"]),
                "Voir historique": False,
                "_modifiee": modif,
            })

    df = pd.DataFrame(rows)

    # Legend explicative
    nb_modif = df["_modifiee"].sum()
    if nb_modif > 0:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:1rem;font-size:0.82rem;color:#6B7280;"
            f"margin-bottom:0.5rem;'>"
            f"<div><span style='background:#FEF3C7;color:#78350F;padding:0.15rem 0.5rem;"
            f"border-radius:4px;font-weight:600;'>🔄 {nb_modif}</span> donnée(s) modifiée(s)</div>"
            f"<div style='color:#9CA3AF;'>Cochez « Voir historique » pour consulter le détail des corrections.</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    # Configuration des colonnes
    disabled_cols = [c for c in df.columns if c not in ("Voir historique", editable_col)] if editable_col else \
                    [c for c in df.columns if c != "Voir historique"]
    
    # Cacher la colonne interne _modifiee
    col_config = {
        "🔄": st.column_config.TextColumn("🔄", width="small", help="Donnée modifiée"),
        "ID": None,
        "_modifiee": None,
        "Voir historique": st.column_config.CheckboxColumn(
            "Voir historique",
            width="small",
            help="Cocher pour afficher l'historique de cette donnée"
        ),
    }

    if editable_col == "Valeur":
        if data_type == "indicateurs":
            col_config["Valeur"] = st.column_config.NumberColumn("Valeur", min_value=0)
        else:
            col_config["Valeur"] = st.column_config.TextColumn("Valeur")

    edited = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(500, 60 + 35 * len(df)),
        disabled=disabled_cols,
        column_config=col_config,
        key=f"data_table_{key_prefix}_{id_lot}"
    )

    # Détection des lignes cochées "Voir historique"
    historique_a_afficher = []
    for i, row in edited.iterrows():
        if row["Voir historique"] and row["_modifiee"]:
            element_lbl = row.get("Indicateur", row.get("Type", "—"))
            historique_a_afficher.append((row["ID"], element_lbl))
        elif row["Voir historique"] and not row["_modifiee"]:
            # Coché mais pas modifié → info
            st.info(f"La donnée #{row['ID']} n'a pas encore été modifiée.")

    # Afficher l'historique des données cochées
    if historique_a_afficher:
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown(
            "<h4 style='color:#374151;font-size:1rem;margin-bottom:0.75rem;'>"
            "Historique des corrections"
            "</h4>",
            unsafe_allow_html=True
        )
        for id_donnee, element_lbl in historique_a_afficher:
            render_historique_donnee(id_donnee, element_lbl)

    return edited if editable_col else None


# ═══════════════════════════════════════════════════════════════
# COMPATIBILITÉ : Ancienne fonction (utilisée dans les pages)
# ═══════════════════════════════════════════════════════════════
def render_historique_complet_lot(id_lot: int, key_prefix: str = ""):
    """
    DEPRECATED : Cette fonction est conservée pour compatibilité.
    Utilisez render_data_table_with_history() à la place.
    """
    # Ne rien afficher : l'historique est maintenant intégré dans le tableau
    pass