<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8">
	<title>Central Server</title>
	<link rel="stylesheet" href="static/TableCSSCode.css" type="text/css"/>
	<!-- SOURCES -->
	<!-- http://www.csstablegenerator.com/ -->
	<!-- http://www.w3schools.com/html/html5_geolocation.asp -->

	<META HTTP-EQUIV="Refresh" CONTENT="30; URL=http://localhost:8080/dashboard">
	<!-- changer la ligne du dessus pour le raspberry -->
</head>
<body>
	<H1>Dashboard</H1>
	<div class="CSSTableGenerator" >
		<table border="1">
			<caption>State of registered thermostats</caption>


			<tr>
				<td>IP Address</td>
				<td>Name</td>
				<td>Type</td>
				<td>Temperature</td>
				<td>Presence</td>
				<td>Valve</td>
			</tr>



			%for row in rows:
				<tr>
				%for col in row:
					<td>{{col}}</td>
				%end
				</tr>
			%end


		</table>
	</div>

    <H1>Control Panel</H1>

	 <form method="POST" action="/temperature">
		 <fieldset>
			 <legend>Settings:</legend>
			 Setpoint Temperature:<br>
			 <input type="text" name="temperature"><br>
			 <input type="submit" value="Submit">
			 <p>The temperature will be reached after 30 minutes</p>
		 </fieldset>
	 </form>
	 <form method="POST" action="/stop">
		 <fieldset>
			 <legend>Stop:</legend>
			 <input type="submit" value="Stop">
			 <p>Cancel the heating process</p>
		 </fieldset>
	 </form>



</body>
