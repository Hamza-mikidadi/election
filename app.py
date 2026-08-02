import streamlit as st
import pandas as pd
import plotly.express as px

# Configuration de la page Streamlit
st.set_page_config(page_title="Élections Bureau Exécutif ACSI 2026", page_icon="🗳️", layout="centered")

# --- LIEN VERS TON GOOGLE SHEET PUBLIÉ EN CSV ---
# Dans Google Sheets : Fichier > Partager > Publier sur le web > onglet des votes > format CSV
# Colle le lien généré ici (remplace l'URL ci-dessous par le tien) :

SHEET_CSV_URL = ""
# ⚠️ gid=0 = premier onglet. Si tes votes sont dans un autre onglet, remplace 0
# par le numéro visible après "gid=" dans l'URL de cet onglet.
# ⚠️ Le Sheet doit être partagé en "Tous les utilisateurs disposant du lien - Lecteur"
# (Partager > Accès général), sinon tu auras une erreur 401.

# --- BARRE LATÉRALE (SIDEBAR) ---
with st.sidebar:
    try:
        st.image("acsi.jpeg", width=80)
    except Exception:
        pass

    st.title("Navigation")
    st.markdown("Sélectionnez le poste dont vous souhaitez voir les résultats :")

    poste_selectionne = st.radio(
        "💼 Postes disponibles :",
        [
            "President",
            "General Secretary",
            "Gen Controller",
            "Financial in Charge",
            "Activitie in Charge",
            "Comm in Charge"
        ]
    )

    st.markdown("---")
    if st.button("🔄 Rafraîchir les résultats"):
        st.cache_data.clear()
        st.rerun()

    st.caption("Élections ACSI 2026\n*United to succeed, committed to the future!*")

# --- ZONE PRINCIPALE (MAIN CONTENT) ---
st.title("🗳️ Élections du Bureau Exécutif ACSI 2026")
st.caption("✨ SOLIDARITY - COMMITMENT - WORK - SUCCESS ✨")
st.markdown("---")

# Détection automatique des colonnes identitaires (email / nom / numéro)
# selon des mots-clés courants dans les formulaires Google
def detecter_colonnes_identite(df):
    mapping = {}
    for col in df.columns:
        col_clean = str(col).upper()
        if "EMAIL" in col_clean or "MAIL" in col_clean or "COURRIEL" in col_clean:
            mapping.setdefault("EMAIL", col)
        elif "NOM" in col_clean or "NAME" in col_clean:
            mapping.setdefault("NOM", col)
        elif "NUM" in col_clean or "TEL" in col_clean or "PHONE" in col_clean:
            mapping.setdefault("NUMERO", col)
    return mapping

# Nettoyage : suppression des doublons (même email OU même nom OU même numéro),
# en gardant le premier bulletin déposé pour chaque personne
def nettoyer_doublons(df):
    colonnes_id = detecter_colonnes_identite(df)
    df_propre = df.copy()
    lignes_supprimees = []

    for cle, col in colonnes_id.items():
        # normalisation légère avant comparaison (espaces, casse)
        norm = df_propre[col].astype(str).str.strip().str.lower()
        est_doublon = norm.duplicated(keep="first") & norm.ne("") & norm.ne("nan")

        if est_doublon.any():
            lignes_supprimees.append(df_propre[est_doublon].assign(_RAISON=f"Doublon sur {col}"))

        df_propre = df_propre[~est_doublon]

    df_supprimees = pd.concat(lignes_supprimees) if lignes_supprimees else df.iloc[0:0]
    nb_supprimes = len(df_supprimees)

    return df_propre, nb_supprimes, colonnes_id, df_supprimees

# Chargement des données directement depuis Google Sheets (mis en cache 60s pour éviter
# de re-télécharger à chaque interaction, mais reste quasi temps réel)
@st.cache_data(ttl=60)
def load_data():
    # keep_default_na=False + na_values=[''] : seules les vraies cellules vides
    # sont traitées comme manquantes. Sans ça, pandas convertit automatiquement
    # le texte "NULL" (et "NA", "None", etc.) en valeur manquante, ce qui
    # supprimait silencieusement les votes pour l'option "NULL".
    df = pd.read_csv(SHEET_CSV_URL, keep_default_na=False, na_values=[''])
    df.columns = df.columns.str.strip().str.upper()
    return df

try:
    data_brute = load_data()
    data, nb_doublons_supprimes, colonnes_identite_detectees, data_supprimees = nettoyer_doublons(data_brute)

    if nb_doublons_supprimes > 0:
        st.warning(
            f"🧹 {nb_doublons_supprimes} bulletin(s) en doublon détecté(s) et retiré(s) "
            f"(sur la base de : {', '.join(colonnes_identite_detectees.keys()) or 'aucune colonne identifiée'})."
        )
        with st.expander(f"🔍 Voir le détail des {nb_doublons_supprimes} bulletin(s) écarté(s)"):
            st.caption("Vérifie ici qu'il ne s'agit pas de faux positifs (ex: homonymes) avant de valider.")
            st.dataframe(data_supprimees, use_container_width=True)
    elif not colonnes_identite_detectees:
        st.info("ℹ️ Aucune colonne email/nom/numéro détectée automatiquement — vérifiez les noms de colonnes si besoin.")

    total_votes = len(data)
    st.metric(label="👥 Nombre Total de Bulletins Déposés", value=total_votes)
    st.markdown(f"### 📊 Résultats : {poste_selectionne}")

    postes_colonnes = {
        "President": "COLONNE 6",
        "General Secretary": "COLONNE 7",
        "Gen Controller": "COLONNE 8",
        "Financial in Charge": "COLONNE 9",
        "Activitie in Charge": "COLONNE 10",
        "Comm in Charge": "COLONNE 11"
    }

    colonne_csv = postes_colonnes[poste_selectionne]

    if colonne_csv not in data.columns:
        st.warning(f"⚠️ La colonne '{colonne_csv}' est introuvable. Titres détectés : {list(data.columns)}")
    else:
        votes_counts = data[colonne_csv].dropna().value_counts().reset_index()
        votes_counts.columns = ['Candidat', 'Voix']

        total_votes_poste = len(data[colonne_csv].dropna())

        if total_votes_poste == 0:
            st.info("Aucun vote n'a encore été enregistré pour cette commission.")
        else:
            votes_counts['Pourcentage'] = (votes_counts['Voix'] / total_votes_poste * 100).round(1)

            fig = px.bar(
                votes_counts,
                x='Candidat',
                y='Voix',
                text=votes_counts['Pourcentage'].astype(str) + '%',
                color='Candidat',
                color_discrete_sequence=px.colors.qualitative.Set2,
                title=f"Suffrages exprimés - {poste_selectionne}"
            )

            fig.update_traces(textposition='outside')
            fig.update_layout(
                showlegend=False,
                xaxis_title="Candidats",
                yaxis_title="Nombre de voix"
            )

            st.plotly_chart(fig, use_container_width=True)

            st.markdown("#### 📋 Détail des voix")
            st.dataframe(
                votes_counts.set_index('Candidat')[['Voix', 'Pourcentage']],
                use_container_width=True
            )

except Exception as e:
    st.error(f"Erreur d'exécution : {e}")
    st.info("Vérifiez que le lien SHEET_CSV_URL est correct et que le Google Sheet est bien publié sur le web.")
