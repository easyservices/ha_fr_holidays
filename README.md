# Vacances scolaires France (custom component Home Assistant)

## En français (see english version below)
Ce composant crée des capteurs Home Assistant indiquant si l'on est en vacances scolaires pour une zone donnée (A, B, C ou DOM) en s'appuyant sur l'open data du ministère de l'Éducation nationale (`data.education.gouv.fr`).

### Fonctionnement
- Télécharge chaque année le calendrier via l'URL API configurable (par défaut la requête v2 avec `year` et `zone` en paramètres) et met le résultat en cache dans `fr_school_data_<annee>.json`.
- Supprime automatiquement le cache de l'année précédente et recharge les données si l'année scolaire change.
- Calcule les états en local selon le fuseau horaire choisi (défaut `Europe/Paris`).
- Expose des attributs communs : `API_URL`, `timezone`, `next_holiday_start`, `next_holiday_end`, `days_until_next_holiday`.

### Capteurs créés
- `sensor.fr_school_is_vacation_time` (booléen) : `on` pendant toute période de vacances pour la zone.
- `sensor.fr_school_is_weekend_time` (booléen) : `on` du samedi au dimanche, y compris pendant les vacances.
- `sensor.fr_school_is_school_day` (booléen) : `on` uniquement les jours de classe (ni week-end ni vacances).
- `sensor.fr_school_summary` (texte) : résumé en français (vacances en cours, week-end, prochaine période, etc.).

### Configuration via l'interface (recommandé)
1. Paramètres → Appareils & services → Ajouter une intégration → rechercher « Vacances scolaires ». 
2. Renseigner `vacation_zone` (ex. `B` pour la zone `B`), laisser l'URL API par défaut ou la personnaliser, choisir les capteurs à créer (`resources`), définir si besoin le `timezone` (ex. `Europe/Paris`).

### Gestion des versions
- 1.2.0: Amélioration des codes erreur et du cache.

### Exemple YAML (mode héritage)
```yaml
sensor:
  - platform: fr_school_holidays
    vacation_zone: "Zone B"
    api_url: "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?limit=99&lang=fr&timezone=Europe%2FParis&refine=start_date:\"{year}\"&refine=zones:\"{zone}\"&refine=population:\"Élèves\"&refine=population:\"-\""
    resources:
      - is_vacation_time
      - is_weekend_time
      - is_school_day
      - summary
    timezone: "Europe/Paris"
```

### Notes
- Dépendance : `aiofiles` (voir `manifest.json`).
- Si l'API est inaccessible, le composant continue d'utiliser le cache de l'année en cours.
- L'intégration est de type « helper » et effectue un polling local, sans équipements supplémentaires.

*Remerciements : Un grand merci à [rt400](https://github.com/rt400/School-Vacation/commits?author=rt400) pour le code original.*

### Licence
License GNU General Public License v2.0 (GPL 2.0).

---
## In English (see french version upper)

### What it does
- Creates Home Assistant sensors that tell whether the chosen French zone (A, B, C or DOM) is on school holidays, using the Education Ministry open-data API.

### How it works
- Fetches the yearly calendar from a configurable API URL (default v2 query with `{year}` and `{zone}` placeholders) and caches it in `fr_school_data_<year>.json`.
- Automatically drops last year's cache and refreshes when the school year changes.
- Computes states locally with the selected timezone (default `Europe/Paris`).
- Exposes shared attributes: `API_URL`, `timezone`, `next_holiday_start`, `next_holiday_end`, `days_until_next_holiday`.

### Entities
- `sensor.fr_school_is_vacation_time` (boolean): `on` during any holiday period for the zone.
- `sensor.fr_school_is_weekend_time` (boolean): `on` from Saturday to Sunday, including holidays.
- `sensor.fr_school_is_school_day` (boolean): `on` only on school days (not weekend, not holiday).
- `sensor.fr_school_summary` (text): human-readable French summary (current holidays, weekend, next period, etc.).

### UI setup (recommended)
1. Settings → Devices & Services → Add Integration → search “French School Holidays”.
2. Provide `vacation_zone` (e.g. `B` for `B Zone`), keep or edit the API URL, pick the sensors (`resources`), set `timezone` (e.g. `Europe/Paris`) if needed.

### Changelogs
- 1.2.0: Cache and http errors codes improved.

### YAML example (legacy)
```yaml
sensor:
  - platform: fr_school_holidays
    vacation_zone: "Zone B"
    api_url: "https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?limit=99&lang=fr&timezone=Europe%2FParis&refine=start_date:\"{year}\"&refine=zones:\"{zone}\"&refine=population:\"Élèves\"&refine=population:\"-\""
    resources:
      - is_vacation_time
      - is_weekend_time
      - is_school_day
      - summary
    timezone: "Europe/Paris"
```

### Notes
- Dependency: `aiofiles` (see `manifest.json`).
- If the API is unreachable, the component keeps using the current-year cache.
- Integration type is “helper” with local polling; no extra hardware.

*Special thanks : Thank you to [rt400](https://github.com/rt400/School-Vacation/commits?author=rt400) for the original version.*

### License
Licensed under GNU General Public License v2.0 (GPL 2.0).