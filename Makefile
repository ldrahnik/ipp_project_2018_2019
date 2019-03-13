# Name:							Lukáš Drahník
# Project: 					Zadání projektu z předmětu IPP 2018/2019
#	Date:							13.3.2019
# Email:						<xdrahn00@stud.fit.vutbr.cz>

LOGIN = xdrahn00
FILES = Makefile parse.php rozsireni interpret.py test.php -C doc readme1.pdf

tar:
	tar -cvzf $(LOGIN).tgz $(FILES)

rmtar:
	rm -f $(LOGIN).tgz

############################################

tex:
	cd doc && make && make readme1.ps && make readme1.pdf
