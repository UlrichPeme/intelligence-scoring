import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Demo - Scoring Crédit", layout="wide")

st.title("🎯 Scoring Comportemental & Matrice de Migration")
st.markdown("Outil d'aide à la décision pour le pilotage du risque de crédit.")

# --- FONCTIONS DE BASE ---

@st.cache_data
def generer_donnees_demo():
    """Génère un dataset de démo avec 100 clients."""
    np.random.seed(42)
    data = {
        'ID_Client': [f"CLI-{str(i).zfill(4)}" for i in range(1, 101)],
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
        # Base de 1000 points
        score = 1000 
        
        # Pénalités (Logique paramétrable)
        score -= (row['Retard_Moyen_Jours'] * 5)
        score -= (row['Incidents_Paiement'] * 50)
        
        if row['Taux_Utilisation_Ligne_%'] > 85:
            score -= 100 # Pénalité pour forte utilisation
            
        # Plancher à 0
        score = max(0, score)
        scores.append(score)
        
        # Mapping Score -> Classe
        if score >= 800: classes.append('A')
        elif score >= 600: classes.append('B')
        elif score >= 400: classes.append('C')
        elif score >= 200: classes.append('D')
        else: classes.append('E')
            
    df_result['Score_Actuel'] = scores
    df_result['Classe_Actuelle'] = classes
    return df_result

# --- INTERFACE UTILISATEUR (SIDEBAR) ---

st.sidebar.header("📥 Import des données")
st.sidebar.info("Le fichier Excel doit contenir : ID_Client, Classe_Precedente, Retard_Moyen_Jours, Incidents_Paiement, Taux_Utilisation_Ligne_%")

fichier_upload = st.sidebar.file_uploader("Charger un fichier Excel (Max 100 lignes)", type=["xlsx"])
utiliser_demo = st.sidebar.checkbox("Utiliser les données de Démo (100 clients)", value=True)

st.sidebar.markdown("---")
st.sidebar.subheader("💡 Optimisez votre gestion des risques")
st.sidebar.write("Vous souhaitez une solution sur-mesure ou automatiser vos reportings ?")
# Remplace par ton vrai lien Calendly ici :
st.sidebar.link_button("📅 Réserver un Audit BI Gratuit", "https://calendly.com/ton-lien-calendly", use_container_width=True)

# --- TRAITEMENT DES DONNÉES ---

df = None

if fichier_upload is not None:
    df_import = pd.read_excel(fichier_upload)
    if len(df_import) > 100:
        st.error("⚠️ Attention : La version démo est limitée à 100 clients. Les lignes supplémentaires seront ignorées.")
        df = df_import.head(100)
    else:
        df = df_import
elif utiliser_demo:
    df = generer_donnees_demo()

# --- AFFICHAGE PRINCIPAL ---

if df is not None:
    # Calcul des nouveaux scores
    df_score = calculer_scoring(df)
    
    # --- PRÉPARATION DES VARIABLES VISUELLES GLOBALES ---
    # Création d'une colonne Tendance visuelle (Flèches)
    mapping_classe = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1}
    
    def obtenir_tendance(row):
        anc = mapping_classe.get(row['Classe_Precedente'], 0)
        nouv = mapping_classe.get(row['Classe_Actuelle'], 0)
        if nouv > anc: return '↗️ Amélioration'
        elif nouv < anc: return '↘️ Dégradation'
        else: return '➡️ Stable'
        
    df_score['Tendance'] = df_score.apply(obtenir_tendance, axis=1)

    # Fonction de style pour la lisibilité (Fond pastel, texte foncé)
    def coloriser_classes(val):
        if val in ['A', 'B']:
            return 'background-color: #d4edda; color: #155724; font-weight: bold;'
        elif val in ['D', 'E']:
            return 'background-color: #f8d7da; color: #721c24; font-weight: bold;'
        elif val == 'C':
            return 'background-color: #fff3cd; color: #856404; font-weight: bold;'
        return ''
    
    # Création d'onglets pour organiser l'affichage
    tab1, tab2, tab3 = st.tabs(["📊 Données & Scoring", "🔀 Dashboard de Migration", "📈 Liste des Risques"])
    
    with tab1:
        st.subheader("Base de données et Résultats du Scoring")
        
        # Affichage dynamique avec Streamlit Column Config
        st.dataframe(
            df_score.style.map(coloriser_classes, subset=['Classe_Actuelle', 'Classe_Precedente']),
            column_config={
                "ID_Client": "ID Client",
                "Classe_Precedente": st.column_config.TextColumn("Ancienne Classe", width="small"),
                "Retard_Moyen_Jours": st.column_config.NumberColumn("Retards", format="%d Jours"),
                "Incidents_Paiement": st.column_config.NumberColumn("Incidents", format="%d"),
                "Taux_Utilisation_Ligne_%": st.column_config.ProgressColumn(
                    "Utilisation Ligne",
                    help="Pourcentage d'utilisation du crédit accordé",
                    format="%.2f %%",
                    min_value=0,
                    max_value=100,
                ),
                "Score_Actuel": st.column_config.NumberColumn("Score / 1000", format="%d pts"),
                "Classe_Actuelle": st.column_config.TextColumn("Nouvelle Classe", width="small"),
                "Tendance": st.column_config.TextColumn("Évolution")
            },
            hide_index=True,
            use_container_width=True,
            height=450
        )

    with tab2:
        st.subheader("📊 Dashboard de Migration du Portefeuille")
        st.markdown("Vue d'ensemble de la dynamique de risque : comment vos clients se sont-ils comportés par rapport au mois dernier ?")

        # --- CALCUL DES KPIS POUR LE DASHBOARD ---
        mapping_num = {'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 5}
        
        df_score['Evol_Risk'] = df_score['Classe_Actuelle'].map(mapping_num) - df_score['Classe_Precedente'].map(mapping_num)
        
        nb_total = len(df_score)
        nb_stable = len(df_score[df_score['Evol_Risk'] == 0])
        nb_degrade = len(df_score[df_score['Evol_Risk'] > 0]) # Risque en hausse
        nb_ameliore = len(df_score[df_score['Evol_Risk'] < 0]) # Risque en baisse
        
        # Focus sur les clients en défaut (D & E)
        d_e_avant = len(df_score[df_score['Classe_Precedente'].isin(['D', 'E'])])
        d_e_apres = len(df_score[df_score['Classe_Actuelle'].isin(['D', 'E'])])
        delta_d_e = d_e_apres - d_e_avant
        
        # --- LIGNE 1 : INDICATEURS CLÉS (KPIS) ---
        col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
        
        col_kpi1.metric("⚖️ Taux de Stabilité", f"{(nb_stable/nb_total)*100:.1f}%", f"{nb_stable} clients")
        col_kpi2.metric("⚠️ Dégradation", f"{(nb_degrade/nb_total)*100:.1f}%", f"{nb_degrade} clients déclassés", delta_color="inverse")
        col_kpi3.metric("✅ Amélioration", f"{(nb_ameliore/nb_total)*100:.1f}%", f"{nb_ameliore} clients surclassés", delta_color="normal")
        col_kpi4.metric("🚨 Portefeuille Douteux (D, E)", f"{d_e_apres} clients", f"{delta_d_e} vs Mois Précédent", delta_color="inverse")
        
        st.markdown("---")
        
        # --- LIGNE 2 : VISUALISATIONS DYNAMIQUES ---
        col_g1, col_g2 = st.columns([1.5, 1])
        ordre_classes = ['A', 'B', 'C', 'D', 'E']
        
        with col_g1:
            st.markdown("**Matrice de Transition**")
            st.caption("📍 *Lecture : Diagonale = Stable. Au-dessus = Dégradation. En-dessous = Amélioration.*")
            
            matrice = pd.crosstab(df_score['Classe_Precedente'], df_score['Classe_Actuelle'])
            matrice = matrice.reindex(index=ordre_classes, columns=ordre_classes, fill_value=0)
            
            # Utilisation de la couleur 'Blues' pour le volume de clients
            fig_hm = px.imshow(
                matrice, 
                text_auto=True, 
                color_continuous_scale='Blues', 
                labels=dict(x="Nouvelle Classe (Post-Scoring)", y="Classe Précédente", color="Volume clients"),
                x=ordre_classes,
                y=ordre_classes,
                aspect="auto"
            )
            # Ajout de la ligne diagonale pour séparer les zones de risque
            fig_hm.add_shape(type="line", x0=-0.5, y0=-0.5, x1=4.5, y1=4.5, line=dict(color="gray", width=2, dash="dash"))
            fig_hm.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            
            st.plotly_chart(fig_hm, use_container_width=True)

        with col_g2:
            st.markdown("**Glissement du Portefeuille**")
            st.caption("Distribution des classes : Avant vs Après.")
            
            # Préparation des données pour le graphique en barres
            dist_avant = df_score['Classe_Precedente'].value_counts().reindex(ordre_classes, fill_value=0)
            dist_apres = df_score['Classe_Actuelle'].value_counts().reindex(ordre_classes, fill_value=0)
            
            df_dist = pd.DataFrame({'Avant': dist_avant, 'Après': dist_apres}).reset_index()
            df_dist = df_dist.melt(id_vars='index', var_name='Période', value_name='Nombre')
            df_dist.rename(columns={'index': 'Classe'}, inplace=True)
            
            # Graphique à barres groupées
            fig_bar = px.bar(
                df_dist, x='Classe', y='Nombre', color='Période', barmode='group',
                color_discrete_map={'Avant': '#A0AEC0', 'Après': '#2B6CB0'}, # Gris vs Bleu
                text_auto=True
            )
            fig_bar.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title=None,
                yaxis_title=None
            )
            
            st.plotly_chart(fig_bar, use_container_width=True)

    with tab3:
        st.subheader("🚨 Clients sous surveillance renforcée")
        st.markdown("Liste des clients ayant basculé dans les **classes de défaut (D ou E)** sur cette période.")
        
        clients_risque = df_score[(df_score['Classe_Actuelle'].isin(['D', 'E'])) & (~df_score['Classe_Precedente'].isin(['D', 'E']))]
        
        if not clients_risque.empty:
            st.dataframe(
                clients_risque[['ID_Client', 'Classe_Precedente', 'Classe_Actuelle', 'Score_Actuel', 'Tendance']].style.map(coloriser_classes, subset=['Classe_Actuelle', 'Classe_Precedente']),
                hide_index=True,
                use_container_width=True
            )
        else:
            st.success("🎉 Excellente nouvelle : Aucun client n'a basculé dans les classes de défaut sur cette période.")

else:
    st.warning("Veuillez charger un fichier ou activer les données de démo dans le menu latéral.")