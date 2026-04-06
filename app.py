import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from fpdf import FPDF
from datetime import datetime
import base64

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="DP-TECH - Scoring Crédit", layout="wide")

st.title("🎯 Scoring Comportemental & Matrice de Migration")
st.markdown("Outil d'aide à la décision pour le pilotage du risque de crédit.")

# --- FONCTIONS DE BASE ---

@st.cache_data
def generer_donnees_demo():
    """Génère un dataset de démo avec 100 clients et secteurs d'activité."""
    np.random.seed(42)
    secteurs_possibles = ['Agro-industrie', 'BTP & Construction', 'Commerce General', 'Transport & Logistique', 'Services & IT']
    
    data = {
        'ID_Client': [f"PME-{str(i).zfill(4)}" for i in range(1, 101)],
        'Secteur_Activite': np.random.choice(secteurs_possibles, 100, p=[0.25, 0.20, 0.35, 0.10, 0.10]),
        'Classe_Precedente': np.random.choice(['A', 'B', 'C', 'D', 'E'], 100, p=[0.3, 0.4, 0.15, 0.1, 0.05]),
        'Retard_Moyen_Jours': np.random.randint(0, 120, 100),
        'Incidents_Paiement': np.random.randint(0, 5, 100),
        'Taux_Utilisation_Ligne_%': np.random.uniform(10, 100, 100).round(2),
    }
    return pd.DataFrame(data)

def calculer_scoring(df):
    """Calcule le score comportemental et attribue la nouvelle classe de risque."""
    df_result = df.copy()
    scores = []
    classes = []
    
    for _, row in df_result.iterrows():
        score = 1000 
        score -= (row['Retard_Moyen_Jours'] * 5)
        score -= (row['Incidents_Paiement'] * 50)
        
        if row['Taux_Utilisation_Ligne_%'] > 85:
            score -= 100 
            
        score = max(0, score)
        scores.append(score)
        
        if score >= 800: classes.append('A')
        elif score >= 600: classes.append('B')
        elif score >= 400: classes.append('C')
        elif score >= 200: classes.append('D')
        else: classes.append('E')
            
    df_result['Score_Actuel'] = scores
    df_result['Classe_Actuelle'] = classes
    
    # Tendance
    mapping_classe = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
    df_result['Tendance'] = df_result.apply(
        lambda r: '↗️ Amélioration' if mapping_classe.get(r['Classe_Actuelle'], 0) > mapping_classe.get(r['Classe_Precedente'], 0)
        else ('↘️ Dégradation' if mapping_classe.get(r['Classe_Actuelle'], 0) < mapping_classe.get(r['Classe_Precedente'], 0) else '➡️ Stable'), axis=1
    )
    
    # Early Warning System (Prédictif)
    def calculer_risque_predictif(row):
        if row['Classe_Actuelle'] in ['D', 'E']: return '⚫ Déjà en Défaut'
        if row['Taux_Utilisation_Ligne_%'] > 90 and row['Retard_Moyen_Jours'] > 30 and row['Tendance'] == '↘️ Dégradation':
            return '🚨 Alerte Rouge (Défaut Imminent)'
        if row['Taux_Utilisation_Ligne_%'] > 85 or row['Incidents_Paiement'] > 0:
            return '🟠 Alerte Orange (À Surveiller)'
        return '🟢 Sain'

    df_result['Alerte_Prédictive'] = df_result.apply(calculer_risque_predictif, axis=1)
    
    return df_result

def generer_rapport_pdf(df_score):
    """Génère un rapport PDF synthétique des risques."""
    pdf = FPDF()
    pdf.add_page()
    
    # En-tête
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Rapport de Comite de Credit", ln=True, align='C')
    pdf.set_font("Arial", 'I', 10)
    pdf.cell(200, 10, txt="Genere par l'outil D&C Intelligence", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Date de l'analyse : {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Calculs pour la synthèse
    nb_total = len(df_score)
    nb_douteux = len(df_score[df_score['Classe_Actuelle'].isin(['D', 'E'])])
    alertes_df = df_score[df_score['Alerte_Prédictive'] == '🚨 Alerte Rouge (Défaut Imminent)']
    nb_alertes = len(alertes_df)
    
    # Section 1
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="1. Synthese globale du portefeuille", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 8, txt=f"- Total des dossiers evalues : {nb_total}", ln=True)
    pdf.cell(200, 8, txt=f"- Clients classes D et E (Douteux) : {nb_douteux}", ln=True)
    pdf.cell(200, 8, txt=f"- Alertes Rouges detectees : {nb_alertes}", ln=True)
    pdf.ln(10)
    
    # Section 2
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, txt="2. Liste des entreprises en Alerte Rouge (Action requise)", ln=True)
    pdf.set_font("Arial", '', 10)
    
    if not alertes_df.empty:
        for _, row in alertes_df.iterrows():
            texte_ligne = f"> {row['ID_Client']} ({row['Secteur_Activite']}) | Retard: {row['Retard_Moyen_Jours']}j | Score: {row['Score_Actuel']} pts"
            pdf.cell(200, 8, txt=texte_ligne, ln=True)
    else:
        pdf.cell(200, 8, txt="Aucune alerte rouge detectee sur cette periode.", ln=True)
        
    # Retourner les bytes du PDF
    return pdf.output(dest='S').encode('latin-1')

# Fonction de style visuel pour les tableaux
def coloriser_classes(val):
    if val in ['A', 'B']: return 'background-color: #d4edda; color: #155724; font-weight: bold;'
    elif val in ['D', 'E']: return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
    elif val == 'C': return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
    return ''

# --- INTERFACE UTILISATEUR (SIDEBAR) ---

st.sidebar.header("📥 Import des données")
st.sidebar.info("Colonnes requises : ID_Client, Secteur_Activite, Classe_Precedente, Retard_Moyen_Jours, Incidents_Paiement, Taux_Utilisation_Ligne_%")

fichier_upload = st.sidebar.file_uploader("Charger un fichier Excel (Max 100 lignes)", type=["xlsx"])
utiliser_demo = st.sidebar.checkbox("Utiliser les données de Démo", value=True)

df = None
if fichier_upload is not None:
    df_import = pd.read_excel(fichier_upload)
    df = df_import.head(100) if len(df_import) > 100 else df_import
elif utiliser_demo:
    df = generer_donnees_demo()

if df is not None:
    df_score = calculer_scoring(df)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("📄 Exporter les résultats")
    pdf_bytes = generer_rapport_pdf(df_score)
    st.sidebar.download_button(
        label="📥 Télécharger le Rapport PDF",
        data=pdf_bytes,
        file_name=f"Rapport_Comite_Credit_{datetime.now().strftime('%Y%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Passez de la démo à vos données")
st.sidebar.write("Découvrez comment nous pouvons adapter ce moteur de scoring comportemental à la réalité spécifique de vos encours.")
st.sidebar.link_button("☕ Réserver un échange avec un expert Data", "https://calendly.com/ulrichpeme/call-datasense", use_container_width=True)

# --- AFFICHAGE PRINCIPAL ---

if df is not None:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Données & Scoring", "🔀 Dashboard de Migration", "📈 Liste des Risques", "🔮 Prédictif & Secteurs"])
    
    with tab1:
        st.subheader("Base de données et Résultats du Scoring")
        st.dataframe(
            df_score.style.map(coloriser_classes, subset=['Classe_Actuelle', 'Classe_Precedente']),
            column_config={
                "ID_Client": "ID Client",
                "Secteur_Activite": "Secteur",
                "Classe_Precedente": st.column_config.TextColumn("Ancienne Classe", width="small"),
                "Retard_Moyen_Jours": st.column_config.NumberColumn("Retards", format="%d Jours"),
                "Incidents_Paiement": st.column_config.NumberColumn("Incidents", format="%d"),
                "Taux_Utilisation_Ligne_%": st.column_config.ProgressColumn(
                    "Utilisation Ligne", format="%.2f %%", min_value=0, max_value=100
                ),
                "Score_Actuel": st.column_config.NumberColumn("Score", format="%d pts"),
                "Classe_Actuelle": st.column_config.TextColumn("Nouvelle Classe", width="small"),
                "Tendance": "Évolution",
                "Alerte_Prédictive": None # On cache la colonne d'alerte dans ce tableau global
            },
            hide_index=True, use_container_width=True, height=450
        )

    with tab2:
        st.subheader("📊 Dashboard de Migration du Portefeuille")
        
        mapping_num = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
        df_score['Evol_Risk'] = df_score['Classe_Actuelle'].map(mapping_num) - df_score['Classe_Precedente'].map(mapping_num)
        
        nb_total = len(df_score)
        nb_stable = len(df_score[df_score['Evol_Risk'] == 0])
        nb_degrade = len(df_score[df_score['Evol_Risk'] > 0])
        nb_ameliore = len(df_score[df_score['Evol_Risk'] < 0])
        d_e_avant = len(df_score[df_score['Classe_Precedente'].isin(['D', 'E'])])
        d_e_apres = len(df_score[df_score['Classe_Actuelle'].isin(['D', 'E'])])
        delta_d_e = d_e_apres - d_e_avant
        
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        col_kpi1.metric("⚖️ Taux de Stabilité", f"{(nb_stable/nb_total)*100:.1f}%", f"{nb_stable} clients")
        col_kpi2.metric("⚠️ Dégradation", f"{(nb_degrade/nb_total)*100:.1f}%", f"{nb_degrade} clients déclassés", delta_color="inverse")
        col_kpi3.metric("✅ Amélioration", f"{(nb_ameliore/nb_total)*100:.1f}%", f"{nb_ameliore} clients surclassés", delta_color="normal")
        col_kpi4.metric("🚨 Portefeuille Douteux (D, E)", f"{d_e_apres} clients", f"{delta_d_e} vs Mois Précédent", delta_color="inverse")
        st.markdown("---")
        
        col_g1, col_g2 = st.columns([1.5, 1])
        ordre_classes = ['A', 'B', 'C', 'D', 'E']
        
        with col_g1:
            st.markdown("**Matrice de Transition**")
            matrice = pd.crosstab(df_score['Classe_Precedente'], df_score['Classe_Actuelle']).reindex(index=ordre_classes, columns=ordre_classes, fill_value=0)
            fig_hm = px.imshow(matrice, text_auto=True, color_continuous_scale='Blues', aspect="auto")
            fig_hm.add_shape(type="line", x0=-0.5, y0=-0.5, x1=4.5, y1=4.5, line=dict(color="gray", width=2, dash="dash"))
            st.plotly_chart(fig_hm, use_container_width=True)

        with col_g2:
            st.markdown("**Glissement du Portefeuille**")
            dist_avant = df_score['Classe_Precedente'].value_counts().reindex(ordre_classes, fill_value=0)
            dist_apres = df_score['Classe_Actuelle'].value_counts().reindex(ordre_classes, fill_value=0)
            df_dist = pd.DataFrame({'Avant': dist_avant, 'Après': dist_apres}).reset_index().melt(id_vars='index', var_name='Période', value_name='Nombre').rename(columns={'index': 'Classe'})
            fig_bar = px.bar(df_dist, x='Classe', y='Nombre', color='Période', barmode='group', color_discrete_map={'Avant': '#A0AEC0', 'Après': '#2B6CB0'}, text_auto=True)
            fig_bar.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.subheader("🚨 Clients sous surveillance renforcée")
        clients_risque = df_score[(df_score['Classe_Actuelle'].isin(['D', 'E'])) & (~df_score['Classe_Precedente'].isin(['D', 'E']))]
        if not clients_risque.empty:
            st.dataframe(clients_risque[['ID_Client', 'Secteur_Activite', 'Classe_Precedente', 'Classe_Actuelle', 'Score_Actuel', 'Tendance']].style.map(coloriser_classes, subset=['Classe_Actuelle', 'Classe_Precedente']), hide_index=True, use_container_width=True)
        else:
            st.success("Aucun client n'a basculé dans les classes de défaut sur cette période.")

    with tab4:
        st.subheader("🔮 Anticipation des Risques & Analyse Sectorielle")
        col_pred1, col_pred2 = st.columns([1, 1])
        
        with col_pred1:
            st.markdown("**🚨 Clients en Alerte Rouge (Défaut probable)**")
            clients_alerte = df_score[df_score['Alerte_Prédictive'] == '🚨 Alerte Rouge (Défaut Imminent)']
            if not clients_alerte.empty:
                st.dataframe(
                    clients_alerte[['ID_Client', 'Secteur_Activite', 'Score_Actuel', 'Taux_Utilisation_Ligne_%']],
                    column_config={"ID_Client": "PME", "Secteur_Activite": "Secteur", "Taux_Utilisation_Ligne_%": st.column_config.ProgressColumn("Tension Tréso", format="%.1f %%", min_value=0, max_value=100)},
                    hide_index=True, use_container_width=True
                )
            else:
                st.success("Aucune Alerte Rouge détectée.")
                
        with col_pred2:
            st.markdown("**🏢 Cartographie du Risque par Secteur**")
            df_score['Est_A_Risque'] = np.where(df_score['Classe_Actuelle'].isin(['D', 'E']) | df_score['Alerte_Prédictive'].isin(['🚨 Alerte Rouge (Défaut Imminent)', '🟠 Alerte Orange (À Surveiller)']), 1, 0)
            df_secteur = df_score.groupby('Secteur_Activite').agg(Total_Clients=('ID_Client', 'count'), Clients_Risque=('Est_A_Risque', 'sum')).reset_index()
            df_secteur['Taux_Risque_%'] = (df_secteur['Clients_Risque'] / df_secteur['Total_Clients']) * 100
            
            fig_secteur = px.bar(
                df_secteur.sort_values('Taux_Risque_%', ascending=False), 
                x='Secteur_Activite', y='Taux_Risque_%',
                text=df_secteur['Clients_Risque'].apply(lambda x: f"{x} clients à risque"),
                color='Taux_Risque_%', color_continuous_scale='Reds'
            )
            fig_secteur.update_traces(textposition='outside')
            fig_secteur.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_secteur, use_container_width=True)
else:
    st.warning("Veuillez charger un fichier ou activer les données de démo dans le menu latéral.")
