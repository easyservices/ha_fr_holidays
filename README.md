Version française *(English version below)*

# Capteurs pour Home Assistant pour déterminer si le jour actuel est une période de vacances scolaires (custom components)

## Récupérer les données des vacances scolaires françaises sous Home Assistant

*Remerciements : Un grand merci à [rt400](https://github.com/rt400/School-Vacation/commits?author=rt400) pour le code original.*

Ce capteur personnalisé détermine si le jour actuel est une période de vacances scolaires dans divers territoires français.

## Guide d'Installation

### Prérequis

Vous pouvez le déployer manuellement comme suit :

- Créez un répertoire nommé `fr_school_holidays` dans le dossier de configuration de votre installation Home Assistant sous `<dossier installation ha>/config/custom_components/`. Si `custom_components` n'existe pas, créez-le également.
- Copiez tous les fichiers du dossier `custom/components/fr_school_holidays` de l'archive ZIP téléchargée depuis le dépôt Git actuel vers le répertoire `fr_school_holidays` que vous venez de créer (dans le dossier de configuration de Home Assistant).
- Ajoutez la configuration suivante dans votre fichier `sensor.yaml` ou directement dans le fichier `config.yaml` de Home Assistant (selon vos préférences pour organiser vos capteurs dans des fichiers de configuration distincts ou tous dans le `config.yaml` de Home Assistant) :

```python
sensor:
  - platform: fr_school_holidays
    # Zones supportées : "Zone A", "Zone B", "Zone C", "Corse", "Guadeloupe", "Guyane", "Martinique", "Mayotte", "Nouvelle Calédonie", "Polynésie", "Réunion", "Saint Pierre et Miquelon", "Wallis et Futuna"
    vacation_zone: "Zone B"
    api_url: 'https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?limit=99&lang=fr&timezone=Europe%2FParis&refine=start_date:"{year}"&refine=zones:"{zone}"&refine=population:"Élèves"&refine=population:"-"'
    resources:
    - is_vacation_time
    - is_weekend_time
    - summary
```

### Détails des Entités
- **is_vacation_time** : Retourne `True` pendant les vacances et `False` autrement.
- **summary** : Fournit une description de la période de vacances actuelle.
- **is_weekend_time** : Retourne `True` pendant le week-end et `False` autrement.

## Utilisation avec capteur `input_boolean`

Ce composant est particulièrement utile lorsqu'il est combiné avec un `input_boolean` dans Home Assistant, permettant des automatisations qui réagissent dynamiquement aux périodes de vacances scolaires.

### Exemple d'Automatisation :
```python
- id: Set_School_Mode_Off
  alias: Désactiver le Mode École
  trigger:
  - platform: state
    entity_id: sensor.fr_school_is_vacation_time
    to: 'True'
  condition: []
  action:
  - data:
      entity_id: input_boolean.school_auto
    service: input_boolean.turn_on
```

## Licence
Sous licence GNU General Public License v2.0 (GPL 2.0).

---
English version *(Version française au-dessus)*


# French School Vacation Sensor as a Custom Component for Home Assistant

## Retrieve French School Vacation Data in Home Assistant

*Acknowledgment: Special thanks to [rt400](https://github.com/rt400/School-Vacation/commits?author=rt400) for the original codebase.*

This custom sensor determines whether the current day is a school holiday in various French territories.

## Installation Guide

### Prerequisites

You can deploy it manually as followed:

- Create a directory named `fr_school_holidays` within your Home Assistant configuration folder under `<ha installation folder>/config/custom_components/`. If `custom_components` does not exist, create it as well.
- Copy all the files from the `custom/components/fr_school_holidays` folder from the zip you downloaded from the current git repo to the `fr_school_holidays` directory you just created (within your Home Assistant configuration folder).
- Include the following configuration in your `sensor.yaml` file or directly into the config.yaml file from Home Assistant (depending on your preferences to have multiple configuration files for each sensor type or all the sensors in the config.yaml from Home Assistant):

```python
sensor:
  - platform: fr_school_holidays
    # Supported zones: "Zone A", "Zone B", "Zone C", "Corse", "Guadeloupe", "Guyane", "Martinique", "Mayotte", "Nouvelle Calédonie", "Polynésie", "Réunion", "Saint Pierre et Miquelon", "Wallis et Futuna"
    vacation_zone: "Zone B"
    api_url: 'https://data.education.gouv.fr/api/explore/v2.1/catalog/datasets/fr-en-calendrier-scolaire/records?limit=99&lang=fr&timezone=Europe%2FParis&refine=start_date:"{year}"&refine=zones:"{zone}"&refine=population:"Élèves"&refine=population:"-"'
    resources:
    - is_vacation_time
    - is_weekend_time
    - summary
```

### Entity Details
- **is_vacation_time**: Returns `True` during vacation periods and `False` otherwise.
- **summary**: Provides descriptive information about the current vacation period.
- **is_weekend_time**: Returns `True` during weekend period and `False` otherwise. 

## Usage with a binary sensor

This component is particularly useful when combined with an `input_boolean` in Home Assistant, enabling automations that respond dynamically to school vacation periods.

### Example Automation:
```python
- id: Set_School_Mode_Off
  alias: Set School Mode Off
  trigger:
  - platform: state
    entity_id: sensor.fr_school_is_vacation_time
    to: 'True'
  condition: []
  action:
  - data:
      entity_id: input_boolean.school_auto
    service: input_boolean.turn_on
```
  
## License
Licensed under GNU General Public License v2.0 (GPL 2.0).

