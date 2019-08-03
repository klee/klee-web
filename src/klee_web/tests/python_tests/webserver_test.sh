echo "Checking that loading the homepage returns 200 OK"
http --check-status http://$(echo $WEBPAGE)/ > /dev/null
