import requests
import json
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import time
import re

from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors
from gensim.scripts.glove2word2vec import glove2word2vec

def requete_nom_propriete(code_item, code_propriete, langue) :
    req = """SELECT ?prop ?propLabel
    WHERE {
      wd:%s ?p wd:%s .
      ?prop wikibase:directClaim ?p .
      SERVICE wikibase:label {
            bd:serviceParam wikibase:language "%s" .
      }
    }""" % (code_item, code_propriete, langue)
    
    par = {
    "query" : req,
    "format" : "json"
    }
    r = requests.get("https://query.wikidata.org/sparql", params=par, headers=headers)

    dico = r.json()
    
    return dico["results"]["bindings"][0]["propLabel"]["value"]

def requete_liste_proprietes(code_item, langue):
    req = """SELECT DISTINCT ?objet ?objetLabel
    WHERE {
      wd:%s ?p ?objet .
      ?objet rdfs:label ?l .
      SERVICE wikibase:label {
            bd:serviceParam wikibase:language "%s" .
      }
    }""" % (code_item, langue)

    par = {
        "query" : req,
        "format" : "json"
    }
    r = requests.get("https://query.wikidata.org/sparql", params=par, headers=headers)

    dico = r.json()
    return dico["results"]["bindings"]

def liste_proprietes(code_item, dico_ranks, langue):
    dic = requete_liste_proprietes(code_item, langue)
    ranks = []
    # Classement des 5 propriétés les plus pertinentes selon les pageRanks
    for propriete in dic:
        uri_objet = propriete["objet"]["value"]
        label_objet = propriete["objetLabel"]["value"]
        code_objet = uri_objet.split("/")[-1]
        if code_objet[1:] in dico_ranks:
            ranks.append((float(dico_ranks[code_objet[1:]]), code_objet, label_objet))
    classement = sorted(ranks, reverse=True)
    mots_nuage = [el[2] for el in classement]
    top = [(el[1], el[2]) for el in classement[:5]]
    #print(classement)
    # Récupération des noms des propriétés
    for propriete in top:
        label_objet = propriete[1]
        code_objet = propriete[0]
        valeur_propriete = requete_nom_propriete(code_item, code_objet, langue)
        if valeur_propriete == "sous-classe de":
            valeur_propriete = "type"
        valeur_propriete = valeur_propriete.capitalize()
        print("%s : %s" % (valeur_propriete, label_objet), end=" | ")
        time.sleep(1.5)
    return mots_nuage

def nuage_de_mots(liste_mots, taille_min, chemin):
    nuage = ""
    s = " -"
    for mot in liste_mots:
        for char in s:
            if char in mot:
                mot = mot.replace(char, "_")
        nuage += mot + " "
    wordcloud = WordCloud(width = 600, height = 600, 
                background_color ='white',
                min_font_size = taille_min).generate(nuage)
    plt.figure(figsize = (8, 8), facecolor = None) 
    plt.imshow(wordcloud) 
    plt.axis("off") 
    plt.tight_layout(pad = 0)
    #plt.show()
    plt.savefig("%s.png" % chemin)


# chargement du dictionnaire des pageRanks

import json

file = open("PageRanks/ranks.json", "r", encoding="utf-8")
dico_ranks = json.load(file)
file.close()

domaines = ["fromages", "peintures"]

dom = int(input("Sur quel domaine voulez-vous obtenir des recommandations ? (0 pour fromages, 1 pour peintures) \n"))

headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36'}

if dom == 0 or dom == 1:
	glove_file = datapath('Données_mémoire/%s_word2vec.txt' % domaines[dom])
	tmp_file = get_tmpfile("test_word2vec.txt")
	_ = glove2word2vec(glove_file, tmp_file)
	model = KeyedVectors.load_word2vec_format(tmp_file)

	par2 = {
		"action" : "wbsearchentities",
		"format" : "json",
		"language" : "fr"
	}

	#Constitution des termes positifs et négatifs pour la recherche de recommandations
	positifs = []
	negatifs = []
	saisie = input("Quel(le) %s aimez-vous ? (0 pour passer à l'étape suivante) \n" % domaines[dom][:-1])
	while saisie != "0":
		positifs.append(saisie)
		saisie = input("Ajouter un(e) autre %s que vous aimez ? (0 pour passer à l'étape suivante)  \n" % domaines[dom][:-1])
	saisie = input("Quel(le) %s n'aimez-vous pas ? (0 pour passer à l'étape suivante)  \n" % domaines[dom][:-1])
	while saisie != "0":
		negatifs.append(saisie)
		saisie = input("Ajouter un(e) autre %s que vous n'aimez pas ? : (0 pour passer à l'étape suivante)  \n" % domaines[dom][:-1])

	recherche = [positifs] + [negatifs]
	
	# recherche des entités recherchées dans la base
	# et récupération de leur lien wikidata dans la liste pos_neg qui sera de longueur 2, d'abord les positifs, puis les négatifs
	pos_neg = []
	for i in range (len(recherche)):
		pos_neg.append([])
		for el in recherche[i]:
			par2["search"] = el
			r = requests.get("https://www.wikidata.org/w/api.php", params=par2)			# peut-être rajouter cette requête dans le dossier ?
			d = r.json()
			for j in range(0, len(d["search"])):
				url_entite = d["search"][j]["concepturi"]
				if "<%s>" % url_entite in model.index2word:
					identifiant = d["search"][j]["id"]
					pos_neg[i].append('<http://www.wikidata.org/entity/%s>' % identifiant)
					break
	
	# Si la recherche est vide
	if pos_neg[0] == [] and pos_neg[1] == []:
		print("Les %s n'ont pas été trouvé(e)s dans la base de données" % domaine[dom])
	else:
		# Utilisation de gensim pour obtenir les recommandations
		res = model.most_similar(positive=pos_neg[0], negative=pos_neg[1], topn=5)
		# Ouverture du fichier json contenant les labels des entités
		labels = open("Labels/liste_labels_%s.json" % domaines[dom], "r", encoding="utf-8")
		dic_labels = json.load(labels)
		labels.close()
		
		liste_mots_nuage = []

		langue = "fr"
		
		print("Voici la liste des %s recommandé(e)s, par ordre de pertinence : " % domaines[dom])
		for el in res:
			print("-"*10)
			entite = el[0][1:-1]
			code_item = entite.split("/")[-1]
			if entite in dic_labels:
				label = dic_labels[entite]
			if (re.match("Q[0-9]+", label)):
				label += " (Pas de label pour cette entité)"
			print(label)
			print("Score : %.3f " % el[1])
			print(entite)
			liste_mots_nuage += liste_proprietes(code_item, dico_ranks, langue)
			print()
		print("-"*10)
		nuage_de_mots(liste_mots_nuage, 30, "Nuages/nuage_script")
else:
	print("Cela ne correspond pas à l'un des domaines, veuillez recommencer")