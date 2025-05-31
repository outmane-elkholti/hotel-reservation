# 🏨 Système de Réservation d'Hôtel

Ce projet est une application web développée avec Django permettant la gestion des réservations d’un hôtel. Il offre une interface claire et intuitive pour les clients comme pour l’administration.

💡 L'application est accessible en ligne ici : [https://honorus.pythonanywhere.com](https://honorus.pythonanywhere.com)

## 🚀 Fonctionnalités

- 👤 Inscription et authentification des utilisateurs
- 🛏️ Gestion des chambres (ajout, modification, suppression)
- 📅 Création et suivi des réservations
- 📊 Tableau de bord pour l’administrateur
- ✉️ Notifications par e-mail (optionnel)
- 📱 Interface responsive adaptée aux mobiles

## 🛠️ Technologies utilisées

- **Backend** : Django (Python)
- **Base de données** : SQLite (par défaut, peut être remplacée par MySQL ou PostgreSQL)
- **Frontend** : HTML5, CSS3, Bootstrap
- **Déploiement** : PythonAnywhere

## 📁 Structure du projet

```bash
hotel-reservation/
│
├── hotel_reservation/       # Répertoire principal du projet Django
├── reservation/             # Application principale : modèles, vues, urls
├── templates/               # Fichiers HTML
├── static/                  # Fichiers statiques (CSS, JS, images)
├── db.sqlite3               # Base de données SQLite
├── manage.py                # Script de gestion du projet Django

