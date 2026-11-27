"""Datos sintéticos usados exclusivamente para pruebas automáticas (nunca en la interfaz)."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class EngineTests(unittest.TestCase):
 def setUp(self):
  sample='Codigo Parque;Nombre Parque;Nombre Localidad;Tipología;Latitud;Longitud\nA-1;Parque Prueba Uno;Suba;Zonal;4.735;-74.105\nA-2;Parque Prueba Dos;Suba;Estructurante;4.725;-74.110\nA-3;Parque Prueba Tres;Kennedy;Vecinal;4.62;-74.14\nA-4;Cancha Fútbol Prueba;Kennedy;Cancha fútbol 5;4.64;-74.15\n'
  rows=server.read_csv(sample.encode())
  recs,sources,warnings=server.build_records([({'title':'Ejemplo sintético de prueba','landing':'','cutoff':'prueba'},rows)])
  server.state.update(records=recs,sources=sources,warnings=warnings,loaded=True)
 def test_csv_loaded(self):
  self.assertEqual(server.get_stats()['total'],4)
  self.assertEqual(server.get_stats()['localities'],2)
 def test_count(self):
  a=server.answer('¿Cuántos parques hay en Suba?')
  self.assertIn('**2 registros**',a['answer'])
  self.assertEqual(a['mode'],'csv_loaded')
 def test_list(self):
  a=server.answer('¿Qué parques hay en Kennedy?')
  self.assertIn('Parque Prueba Tres',a['answer'])
  self.assertNotIn('Parque Prueba Uno',a['answer'])
 def test_compare(self):
  a=server.answer('Compara Suba y Kennedy')
  self.assertIn('Suba: 2 registros',a['answer'])
  self.assertIn('Kennedy: 2 registros',a['answer'])
 def test_unsupported(self):
  a=server.answer('¿Puedo reservar una cancha para hoy?')
  self.assertIn('No dispongo de información',a['answer'])
 def test_sport(self):
  a=server.answer('¿Qué canchas de fútbol hay en Kennedy?')
  self.assertEqual(len(a['results']),1)
  self.assertIn('Cancha Fútbol Prueba',a['answer'])
 def test_typology(self):
  a=server.answer('¿Qué tipos de parques hay?')
  self.assertIn('Vecinal',a['answer'])
 def test_missing_coordinates(self):
  rows=server.read_csv(b'Nombre Parque,Localidad\nParque Prueba,Suba')
  recs,_,_=server.build_records([({'title':'sin coordenadas','landing':'','cutoff':''},rows)])
  self.assertEqual(len(recs),1)
  self.assertIsNone(recs[0]['coords'])
 def test_snapshot_does_not_fabricate_rows(self):
  server.state.update(records=[],sources=[],warnings=[],loaded=False)
  a=server.answer('¿Qué parques hay en Suba?')
  self.assertEqual(a['mode'],'snapshot')
  self.assertEqual(len(a['results']),0)
 def test_no_exaggerated_scope(self):
  a=server.answer('¿Cuántos parques hay en toda Bogotá?')
  self.assertIn('no necesariamente a todos',a['answer'])

if __name__=='__main__':unittest.main()
