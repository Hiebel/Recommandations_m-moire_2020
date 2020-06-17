import requests
import json
import re

from gensim.test.utils import datapath, get_tmpfile
from gensim.models import KeyedVectors
from gensim.scripts.glove2word2vec import glove2word2vec

domaines = ["fromages", "peintures"]

dom = int(input("Sur quel domaine voulez-vous obtenir des recommandations ? (0 pour fromages, 1 pour peintures) \n"))

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
		print("-"*10)
else:
	print("Cela ne correspond pas à l'un des domaines, veuillez recommencer")