CRITERIOS_POR_AREA = {
    "traumatismos": [
    {
      "criterio": "mecanismo de lesion",
      "pregunta": "como ocurrio el traumatismo? describa el evento con el mayor detalle posible (ej: caida de una escalera, accidente de trafico, golpe directo, etc.). incluya la altura de la caida si aplica.",
      "peso": 9
    },
    {
      "criterio": "parte del cuerpo afectada",
      "pregunta": "que parte de su cuerpo resulto afectada? sea lo mas especifico posible (ej: rodilla derecha, tobillo izquierdo, craneo, etc.).",
      "peso": 8
    },
    {
      "criterio": "tiempo de ocurrencia",
      "pregunta": "cuando ocurrio el traumatismo? (fecha y hora aproximada).",
      "peso": 2
    },
    {
      "criterio": "intensidad del impacto",
      "pregunta": "como describiria la intensidad del impacto? (ej: leve, moderado, severo. si fue una caida, desde que altura? si fue un golpe, que objeto lo provoco y con que fuerza?).",
      "peso": 3
    },
    {
      "criterio": "perdida de conocimiento",
      "pregunta": "perdio el conocimiento despues del traumatismo? si es asi, por cuanto tiempo?",
      "peso": 4
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta algun otro sintoma ademas del dolor en el area afectada? (ej: nauseas, vomitos, mareos, entumecimiento, hormigueo, debilidad, dificultad para respirar, etc.).",
      "peso": 1
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "recibio algun tipo de atencion medica o tratamiento previo por este traumatismo? (ej: primeros auxilios, inmovilizacion, analgesicos, etc.) si es asi, describa el tratamiento recibido.",
      "peso": 7
    },
    {
      "criterio": "medicamentos actuales",
      "pregunta": "que medicamentos esta tomando actualmente (incluyendo analgesicos, antiinflamatorios, anticoagulantes, etc.)?",
      "peso": 9
    }
  ],
  "intoxicaciones": [
    {
      "criterio": "sustancia implicada",
      "pregunta": "que sustancia sospecha que ha sido ingerida o inhalada? (si es posible, describa el envase o proporcione imagenes).",
      "peso": 1
    },
    {
      "criterio": "via de exposicion",
      "pregunta": "como ocurrio la intoxicacion? (ingestion, inhalacion, contacto cutaneo, inyeccion). describa la situacion con detalle.",
      "peso": 3
    },
    {
      "criterio": "tiempo de exposicion",
      "pregunta": "cuanto tiempo estuvo expuesto a la sustancia? a que hora ocurrio el incidente?",
      "peso": 10
    },
    {
      "criterio": "cantidad de sustancia",
      "pregunta": "que cantidad de la sustancia cree que fue ingerida, inhalada o con la que estuvo en contacto? (si es posible, proporcione informacion sobre el envase o la concentracion).",
      "peso": 8
    },
    {
      "criterio": "sintomas actuales",
      "pregunta": "describa los sintomas que presenta actualmente. indique la intensidad (leve, moderada, severa) y el tiempo de inicio de cada sintoma.",
      "peso": 2
    },
    {
      "criterio": "antecedentes medicos relevantes",
      "pregunta": "tiene alguna enfermedad preexistente (alergias, enfermedades cardiacas, pulmonares, hepaticas, renales)? esta tomando algun medicamento actualmente?",
      "peso": 10
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tipo de tratamiento antes de contactarme? (ej: lavado gastrico, administracion de antidoto). si es asi, describa.",
      "peso": 5
    },
    {
      "criterio": "contexto ambiental",
      "pregunta": "donde ocurrio la intoxicacion? describa el entorno (ej: hogar, trabajo, exterior). habia otras personas expuestas? presentan sintomas similares?",
      "peso": 7
    }
  ],
  "enfermedades infecciosas": [
    {
      "criterio": "inmunocompetencia",
      "pregunta": "tiene alguna condicion medica que comprometa su sistema inmunologico (ej. vih, cancer, diabetes, tratamiento con inmunosupresores)?",
      "peso": 6
    },
    {
      "criterio": "fiebre",
      "pregunta": "presenta fiebre? si es asi, cual es la temperatura maxima que ha registrado y con que frecuencia la presenta? (incluir instrucciones para la toma de temperatura si es necesario).",
      "peso": 6
    },
    {
      "criterio": "sintomas respiratorios",
      "pregunta": "presenta tos, dificultad para respirar, dolor de garganta, secrecion nasal, congestion nasal o estornudos? (especificar caracteristicas de la tos: productiva/seca, tipo de esputo si lo hay).",
      "peso": 4
    },
    {
      "criterio": "sintomas gastrointestinales",
      "pregunta": "presenta nauseas, vomitos, diarrea, dolor abdominal o estrenimiento? (especificar caracteristicas de la diarrea: frecuencia, consistencia, presencia de sangre o moco).",
      "peso": 8
    },
    {
      "criterio": "sintomas cutaneos",
      "pregunta": "presenta erupciones cutaneas, sarpullido, ampollas, o alguna otra alteracion en la piel?(pedir descripcion y si es posible una foto).",
      "peso": 1
    },
    {
      "criterio": "exposicion a agentes infecciosos",
      "pregunta": "ha estado expuesto recientemente a alguna persona con una enfermedad infecciosa? ha viajado recientemente? ha tenido contacto con animales o alimentos potencialmente contaminados? (especificar lugares visitados, tipo de animales y alimentos).",
      "peso": 8
    },
    {
      "criterio": "vacunacion",
      "pregunta": "esta al dia con sus vacunas? ha recibido alguna vacuna recientemente? (especificar vacunas recibidas y fechas si es posible).",
      "peso": 1
    },
    {
      "criterio": "uso de antibioticos previos",
      "pregunta": "ha utilizado antibioticos recientemente? si es asi, cual y por cuanto tiempo? (importante para determinar posibles resistencias bacterianas).",
      "peso": 5
    }
  ],
  "enfermedades parasitarias": [
    {
      "criterio": "sintomas gastrointestinales",
      "pregunta": "describa con detalle los sintomas gastrointestinales presentes: diarrea (consistencia, frecuencia, presencia de sangre o moco), nauseas, vomitos, dolor abdominal (ubicacion, caracteristicas), perdida de apetito.",
      "peso": 6
    },
    {
      "criterio": "sintomas extraintestinales",
      "pregunta": "presenta sintomas fuera del tracto gastrointestinal, como fiebre, tos, erupciones cutaneas, hinchazon, perdida de peso, anemia, dolor muscular o articular? describalos con detalle.",
      "peso": 10
    },
    {
      "criterio": "historia de viajes recientes",
      "pregunta": "ha viajado recientemente a alguna zona geografica con alta prevalencia de parasitosis? si es asi, especifique el lugar, las fechas y el tipo de alojamiento.",
      "peso": 10
    },
    {
      "criterio": "exposicion a agua o alimentos contaminados",
      "pregunta": "ha consumido agua o alimentos que puedan estar contaminados (ej., agua no potable, alimentos crudos o mal cocidos, contacto con heces)? describa la situacion.",
      "peso": 2
    },
    {
      "criterio": "contacto con animales",
      "pregunta": "ha tenido contacto con animales (ej., mascotas, ganado) que puedan ser portadores de parasitos? describa el tipo de contacto y los animales involucrados.",
      "peso": 9
    },
    {
      "criterio": "antecedentes de parasitosis previas",
      "pregunta": "ha tenido alguna parasitosis diagnosticada previamente? si es asi, especifique el tipo de parasito y el tratamiento recibido.",
      "peso": 8
    },
    {
      "criterio": "uso de medicamentos previos",
      "pregunta": "ha tomado algun medicamento recientemente (antibioticos, antiparasitarios, etc.) que pueda afectar los resultados de las pruebas? especifique el nombre y la dosis del medicamento.",
      "peso": 4
    }
  ],
  "enfermedades de la piel": [
    {
      "criterio": "localizacion",
      "pregunta": "en que parte del cuerpo se encuentra la lesion o afeccion de la piel? por favor, sea lo mas especifico posible (ej: cara, brazo derecho, entre los dedos del pie izquierdo). si son multiples lesiones, describa la localizacion de cada una.",
      "peso": 3
    },
    {
      "criterio": "tipo de lesion",
      "pregunta": "puede describir la lesion? (ej: mancha, roncha, papula, pustula, vesicula, placa, nodulo, ulcera, erosion, descamacion, etc.). si es posible, adjunte una fotografia clara de la lesion con buena iluminacion.",
      "peso": 2
    },
    {
      "criterio": "evolucion temporal",
      "pregunta": "cuanto tiempo lleva presentando la lesion o afeccion? ha cambiado de aspecto con el tiempo? como ha evolucionado (aumentado de tamano, cambiado de color, aumentado o disminuido en numero, etc.)?",
      "peso": 6
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta algun sintoma ademas de la lesion cutanea? (ej: picazon, dolor, ardor, hinchazon, fiebre, malestar general, etc.) describa la intensidad de cada sintoma.",
      "peso": 7
    },
    {
      "criterio": "antecedentes personales",
      "pregunta": "tiene antecedentes personales de enfermedades de la piel? ha tenido alguna alergia en la piel anteriormente? utiliza algun medicamento de forma regular? ha estado expuesto a algun irritante o alergeno recientemente (plantas, cosmeticos, detergentes, metales, etc.)?",
      "peso": 2
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay algun antecedente familiar de enfermedades de la piel?",
      "peso": 2
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "ha notado algun factor que pueda haber desencadenado la aparicion o empeoramiento de la lesion? (ej: exposicion solar, estres, cambios hormonales, contacto con sustancias irritantes, etc.)",
      "peso": 4
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tratamiento previamente para esta lesion o afeccion? cual fue el tratamiento y cual fue la respuesta?",
      "peso": 3
    }
  ],
  "consulta seguimiento examen": [
  {
    "criterio": "sintomas_actuales_desde_examen",
    "pregunta": "¿Se ha preguntado si el paciente ha tenido nuevos síntomas o cambios desde que se realizó el examen?",
    "peso": 8
  },
  {
    "criterio": "correlacion_clinica_resultado",
    "pregunta": "¿Se ha relacionado adecuadamente el resultado del examen con el cuadro clínico del paciente?",
    "peso": 6
  },
  {
    "criterio": "interpretacion_medica_resultado",
    "pregunta": "¿Se ha documentado la interpretación médica del resultado (normal, anormal, requiere seguimiento, etc.)?",
    "peso": 6
  },
  {
    "criterio": "plan_manejo_según_resultado",
    "pregunta": "¿Se modifica o se mantiene el plan de tratamiento según el resultado de examen?",
    "peso": 6
  }
],
"sospecha de dengue": [
    {
        "criterio": "inicio_fiebre_fecha", 
        "pregunta": "¿Cuándo inició la fiebre?", 
        "peso": 8
    },
    {
        "criterio": "presencia_petequias", 
        "pregunta": "¿Presenta petequias?", 
        "peso": 8
    },
    {
        "criterio": "diuresis_frecuencia_24h", 
        "pregunta": "¿Ha orinado al menos 4 veces en las últimas 24 horas?", 
        "peso": 6
    },
    {
        "criterio": "tolerancia_liquidos_via_oral", 
        "pregunta": "¿Tolera líquidos o presenta vómitos?", 
        "peso": 6
    },
    {
        "criterio": "sintomas_gastrointestinales_presentes", 
        "pregunta": "¿Presenta síntomas gastrointestinales?", 
        "peso": 6
    },
    {
        "criterio": "sangrado_mucosas_escleras", 
        "pregunta": "¿Presenta sangrado en mucosas o escleras?", 
        "peso": 10
    },
    {
        "criterio": "nexo_epidemiologico_casos_zona", 
        "pregunta": "¿Hay casos de dengue en su comunidad?", 
        "peso": 5
    },
    {
        "criterio": "dolor_articular_reportado", 
        "pregunta": "¿Presenta dolor en las articulaciones?", 
        "peso": 4
    },
    {
        "criterio": "signos_alarma_especificados", 
        "pregunta": "¿La nota médica aclara signos de alarma?", 
        "peso": 6
    },
    {
        "criterio": "comorbilidades_relevantes", 
        "pregunta": "¿Tiene comorbilidades como diabetes o hipertensión?", 
        "peso": 6
    },
    {
        "criterio": "ubicacion_48h_previas", 
        "pregunta": "¿Dónde se encontraba hace 48 horas, considerando que los síntomas comenzaron hace aproximadamente 24 horas?", 
        "peso": 5
    },
    {
        "criterio": "casos_dengue_en_vivienda_o_comunidad",
        "pregunta": "¿Hay casos de dengue en su vivienda o en su comunidad?",
        "peso": 6
    }
],
  "alergia y trastornos inmunitarios": [
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existe algun antecedente familiar de alergias o trastornos inmunitarios?",
      "peso": 4
    },
    {
      "criterio": "edad de inicio",
      "pregunta": "a que edad comenzaron los sintomas alergicos o inmunitarios?",
      "peso": 8
    },
    {
      "criterio": "tipo de alergia",
      "pregunta": "a que tipo de material es alergico (polen, alimentos, medicamentos, etc.)?",
      "peso": 6
    },
    {
      "criterio": "sintomas",
      "pregunta": "cuales son los sintomas que presenta (rinorrea, urticaria, dificultad para respirar, etc.)?",
      "peso": 8
    },
    {
      "criterio": "severidad",
      "pregunta": "que tan severos son los sintomas? (leve, moderado, grave)",
      "peso": 6
    },
    {
      "criterio": "frecuencia",
      "pregunta": "con que frecuencia presenta los sintomas?",
      "peso": 4
    },
    {
      "criterio": "tratamientos previos",
      "pregunta": "que tratamientos ha recibido anteriormente para sus alergias o trastornos inmunitarios?",
      "peso": 6
    },
    {
      "criterio": "exposicion a alergenos",
      "pregunta": "ha estado expuesto recientemente a algun material que cuase alergia conocida?",
      "peso": 5
    }
  ],
  "embarazo que finaliza en aborto": [
    {
      "criterio": "fecha de la ultima menstruacion (fum)",
      "pregunta": "cual fue la fecha de su ultima menstruacion?",
      "peso": 7
    },
    {
      "criterio": "numero de semanas de gestacion al momento del aborto",
      "pregunta": "cuantas semanas de embarazo tenia cuando ocurrio el aborto?",
      "peso": 9
    },
    {
      "criterio": "tipo de aborto",
      "pregunta": "fue un aborto espontaneo, provocado o incompleto?",
      "peso": 6
    },
    {
      "criterio": "sintomas experimentados antes del aborto",
      "pregunta": "experimento algun sintoma antes del aborto, como sangrado vaginal, dolor abdominal o contracciones?",
      "peso": 5
    },
    {
      "criterio": "cantidad de sangrado",
      "pregunta": "cuanta sangre perdio? (describa la cantidad o use una referencia como toallas sanitarias usadas)",
      "peso": 4
    },
    {
      "criterio": "antecedentes de abortos previos",
      "pregunta": "ha tenido abortos anteriormente? si es asi, cuantos?",
      "peso": 8
    },
    {
      "criterio": "uso de medicamentos o drogas",
      "pregunta": "estaba tomando algun medicamento o droga durante el embarazo?",
      "peso": 8
    },
    {
      "criterio": "estado emocional de la paciente",
      "pregunta": "como se siente emocionalmente tras el aborto?",
      "peso": 5
    },
    {
      "criterio": "Atenciòn Mèdica",
      "pregunta": "Recibiò Atenciòn hospitalaria por el aborto",
      "peso": 6
    },
    {
      "criterio": "Fecha del aborto",
      "pregunta": "En que fecha verificò el aborto",
      "peso": 7
    },
    {
      "criterio": "Dìas post aborto",
      "pregunta": "total de dìas post aborto",
      "peso": 6
    },
    {
      "criterio": "Planificacion familiar post aborto",
      "pregunta": "usa mètodo de planificaciòn familiar posterior al aborto",
      "peso": 5
    },
    {
      "criterio": "Perìodo intergenèsico",
      "pregunta": "En que fecha finalizo su embarazo anterior o su aborto anterior?",
      "peso": 4
    },
    {
      "criterio": "Infecciòn Pèlvica",
      "pregunta": "Fiebre? dolor de cuerpo? escalofrìos? dolor pèlvico? Sangrado transvaginal fètido?",
      "peso": 5
    }
  ],
  "complicaciones relacionadas con el puerperio": [
    {
      "criterio": "hemorragia postparto",
      "pregunta": "nùmero de toallas sanitarias o compresas utilizadas en las ùltimas 24 horas? presenta coàgulos? duraciòn  del  sangrado? frialdad manos y pies? sensacion de debilidad? mareos?",
      "peso": 7
    },
    {
      "criterio": "infeccion puerperal",
      "pregunta": "tiene fiebre o tiene dolor de cuerpo y escalofrìos?, dolor de vientre  o en la zona genital de fuerte intensidad ? color del  sangrado vaginal?  sangrado vaginal con mucho mal olor?",
      "peso": 8
    },
    {
      "criterio": "trombosis venosa profunda",
      "pregunta": "presenta dolor, hinchazon o enrojecimiento en las piernas?",
      "peso": 6
    },
    {
      "criterio": "depresion posparto",
      "pregunta": "llora con fàcilidad? se siente triste? ansiosa ?  desesperanzada?   ocasionalmente? no tiene animos para realizar el cuidado de su bebe y su cuidado personal? ha perdido el apetito?  no puede conciliar el sueño?",
      "peso": 7
    },
    {
      "criterio": "estado de animo general",
      "pregunta": " la mayor parte del tiempre su estado de ànimo es: alegre, ansiosa, triste, enojada?",
      "peso": 6
    },
    {
      "criterio": "Preclamsia Post Parto",
      "pregunta": "dolor en toda la cabeza de fuerte intensidad? ve lucitas? zumbido de oidos? hinchazòn en las piernas? dolor en la boca del estòmago de fuerte intensidad?",
      "peso": 10
    },
    {
      "criterio": "Mastitis",
      "pregunta": "fiebre? pechos congestionados? dolor intenso? calor y enrojecimiento en piel?",
      "peso": 5
    },
    {
      "criterio": "Parto vaginal ",
      "pregunta": "Su parto fue vaginal ?",
      "peso": 4
    },
    {
      "criterio": "Parto via cesarea",
      "pregunta": "su parto fue cesàrea?",
      "peso": 4
    },
    {
      "criterio": "Deshicencia de Episiotomìa",
      "pregunta": "al revisar su herida de episiotamia la nota abierta? la abertura es grande o pequeña? observa pus? dolor intenso?",
      "peso": 6
    },
    {
      "criterio": "Infecciòn de herida operatoria",
      "pregunta": "fiebre? enrojecimiento visible? salida de pus a travez de la curaciòn? salida de sangre que atraviesa la curaciòn?",
      "peso": 6
    }
  ],
  "trastornos del embarazo y parto": [
    {
      "criterio": "Fecha de ultima regla ",
      "pregunta": "en que fecha iniciò de su ultima menstruaciòn?",
      "peso": 10
    },
    {
      "criterio": "Semanas de embarazo",
      "pregunta": "cuantas semanas de embarazo presenta a la fecha?",
      "peso": 8
    },
    {
      "criterio": "Edad actual",
      "pregunta": "mayor de 35 años ? edad ,menor o igual a 19 años? ",
      "peso": 7
    },
    {
      "criterio": "Multaparidad",
      "pregunta": "Cuantos embarazos ha tenido incluyendo este?      cuantos terminaron en parto?",
      "peso": 7
    },
    {
      "criterio": "Abortos previos",
      "pregunta": "ha tenido abortos? cuantos?",
      "peso": 7
    },
    {
      "criterio": "hijos vivos",
      "pregunta": "cuantos hijos tiene vivos?                      si alguno de sus hijos murio  dentro de los 28 dìas  de vida?    ",
      "peso": 7
    },
    {
      "criterio": "Partos prematuro",
      "pregunta": "ha tenido hijos prematuros? cuantos?",
      "peso": 7
    },
    {
      "criterio": "Tipo sanguìneo",
      "pregunta": "su tipo sanguìneo en ORH negativo",
      "peso": 5
    },
    {
      "criterio": "Enfermedades cronicas de riesgo",
      "pregunta": "Diabetes? Hipertensiòn? otra enfermedad crònica?",
      "peso": 7
    },
    {
      "criterio": "Estados nutricional de riego",
      "pregunta": "Obesidad?        Delgadez?      si  conoce su peso y talla escribalo",
      "peso": 5
    },
    {
      "criterio": "Perìodo intergenèsico corto",
      "pregunta": "Fecha de su ùltimo parto? si su embarazo no culmino en parto fecha de la terminaciòn de su embarazo? complicaciòn(es) en su(s) embarazos anteriore(S)?  diagnòstico?  ",
      "peso": 5
    },
    {
      "criterio": "Aborto habitual",
      "pregunta": "Abortos a repeticiòn?    cuantos?",
      "peso": 8
    },
    {
      "criterio": "Embarazo no deseado",
      "pregunta": "Es un embarazo no deseado?",
      "peso": 8
    },
    {
      "criterio": "Antecedente de transtorano hipertensivo del embarazo ",
      "pregunta": "Presento transtorno hipertensivo del embarazo en sugestacion anterior? (preclampsia, eclamsia o sindrome de Help",
      "peso": 10
    },
    {
      "criterio": "Anrecedente diabetes gestacional",
      "pregunta": "presentò diabetes gestacional en su gestaciòn anterior?",
      "peso": 10
    },
    {
      "criterio": "Complicaciones en embarzo anterior",
      "pregunta": " complicaciòn(es) en su(s) embarazos anteriore(S)?  diagnòstico?  ",
      "peso": 8
    },
    {
      "criterio": "Amenaza de aborto/ Aborto espontàneo",
      "pregunta": " Presenta en este momento sangrado transvaginal? desde cuando?  cantidad? color? olor? se acompaña  dolor en espalda baja y el vientre? ha  explusado restos como carne molida?",
      "peso": 10
    },
    {
      "criterio": "Hiperemèsis Gravidica",
      "pregunta": "Presenta vòmitos persistentes? nùmero de vòmitos en las ùltimas 24 horas? le impiden la ingesta adecuada de alimentos?",
      "peso": 10
    },
    {
      "criterio": "Infecciòn vìas Urinarias/Pielonefritis",
      "pregunta": "Ardor al orinar? orina màs amarillo de lo normal? dolor en el vientre al orinar? sangre en la orina? dolor en espalda baja? fiebre de 38C ò màs?",
      "peso": 10
    },
    {
      "criterio": "Enfermedad Trofoblàstica",
      "pregunta": "Sangrado con expulsiò de vesiculas parecidas a uvas blancas por vagina?        se acompaña de vòmitos y nauseas intensas?",
      "peso": 10
    },
    {
      "criterio": "Infecciòn vias urinarias/Pielonefritis",
      "pregunta": "Ardor al orinar? orina màs amarillo de lo normal? dolor en el vientre al orinar? sangre en la orina? dolor en espalda baja? fiebre de 38C ò màs?",
      "peso": 8
    },
    {
      "criterio": "Amenaza de aborto/aborto espontàneo",
      "pregunta": " Presenta en este momento sangrado transvaginal? desde cuando?  cantidad? color? olor? se acompaña  dolor en espalda baja y el vientre? ha  explusado restos como carne molida?",
      "peso": 9
    },
    {
      "criterio": "Placenta Previa",
      "pregunta": "Presenta Sangrado transvaginal  indoloro?  cantidad?",
      "peso": 7
    },
    {
      "criterio": "Abrupcio de placenta",
      "pregunta": "Presenta Sangrado transvaginal ? cantidad?  acompaña de dolor intenso y endurecimiento del ùtero? ",
      "peso": 10
    },
    {
      "criterio": "Transtorno hipertensivo del embarazo (a partir de las 20 semanas)",
      "pregunta": "Semanas de embarazo? Valor de su ùlima toma de presiòn arterial?  fecha de la toma? Hora de la toma ? tiene dolor de cabeza de fuerte intensidad? el dolor de cabeza se acompaña de zumbido de oidos? ve lucitas? Tiene dolor en la boca del estòmago fuerte? tiene hinchados los pies? tiene  hinchadas las manos? tiene hinchada la cara?",
      "peso": 8
    },
    {
      "criterio": "Ruptura Prematura de Membranas",
      "pregunta": "Presenta salida de lìquido por la vagina? desde hace cuanto? cantidad?  el olor es similar a lejìa?  ",
      "peso": 10
    },
    {
      "criterio": "Hipomotilidad fetal",
      "pregunta": "disminucion de los movimientos fetales desde cuando?",
      "peso": 10
    },
    {
      "criterio": "Obito fetal",
      "pregunta": " NO percibe ningùn movimiento fetal? desde cuando?",
      "peso": 10
    },
    {
      "criterio": "Transtorno hipertensivo del embarazo",
      "pregunta": "Valor de su ùlima toma de presiòn arterial?  fecha de la toma? Hora de la toma ? tiene dolor de cabeza de fuerte intensidad? el dolor de cabeza se acompaña de zumbido de oidos? ve lucitas? Tiene dolor en la boca del estòmago fuerte? tiene hinchados los pies? tiene  hinchadas las manos? tiene hinchada la cara?",
      "peso": 10
    },
    {
      "criterio": "fiebre",
      "pregunta": "Presenta fiebre? es fuerte, regular o suave?   se acompaña de dolor de cuerpo y escalofrios? se acompaña de dolor de cabeza? se acompaña de dolor similar al del parto?",
      "peso": 10
    },
    {
      "criterio": "Infecciòn vias urinarias/Pielonefritis",
      "pregunta": "Ardor al orinar? orina màs amarillo de lo normal? dolor en el vientre al orinar? sangre en la orina? dolor en espalda baja? fiebre de 38C ò màs?",
      "peso": 8
    },
    {
      "criterio": "Amenaza de parto  prematuro",
      "pregunta": "semanas de embarazo , Presenta dolor que inicia en la espalda y se le viene para el vientre? ha expulsado moco con sangre por la vagina?",
      "peso": 10
    }
  ],
  "enfermedades de la sangre o de los organos hematopoyeticos": [
    {
      "criterio": "historia familiar",
      "pregunta": "existe algun antecedente familiar de enfermedades hematologicas como anemia, leucemia, hemofilia o trastornos de la coagulacion?",
      "peso": 10
    },
    {
      "criterio": "sintomas",
      "pregunta": "presenta algun sintoma como fatiga, debilidad, palidez, dificultad respiratoria, sangrado o moretones inusuales, fiebre o infecciones recurrentes?",
      "peso": 9
    },
    {
      "criterio": "medicación",
      "pregunta": "esta tomando algun medicamento actualmente? (incluyendo suplementos, hierbas o medicamentos de venta libre)",
      "peso": 6
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "ha padecido alguna enfermedad o condicion medica previamente, como infecciones virales o bacterianas severas, enfermedades autoinmunes, o tratamientos con quimioterapia o radioterapia?",
      "peso": 9
    },
    {
      "criterio": "habitos",
      "pregunta": "podria describir sus habitos relacionados con el consumo de alcohol, tabaco, o drogas? consume una dieta balanceada?",
      "peso": 7
    },
    {
      "criterio": "exposicion",
      "pregunta": "ha estado expuesto recientemente a algun quimico toxico, radiacion o pesticida?",
      "peso": 8
    },
    {
      "criterio": "signos vitales",
      "pregunta": "podria indicar su frecuencia cardiaca, presion arterial y temperatura actual (si cuenta con instrumentos en casa)?",
      "peso": 8
    },
    {
      "criterio": "examen fisico",
      "pregunta": "podria describir cualquier signo visible que haya notado, como cambios en la piel (cambios de coloración), ganglios linfaticos inflamados o cualquier otra anomalia?",
      "peso": 7
    }
  ],
  "enfermedades del oído o de la apófisis mastoides": [
    {
      "criterio": "otalgia",
      "pregunta": "presenta dolor de oido? si es asi, describa la intensidad y localizacion del dolor.",
      "peso": 6
    },
    {
      "criterio": "hipoacusia",
      "pregunta": "ha experimentado alguna disminucion de la audicion? en que oido? de manera subita o gradual?",
      "peso": 8
    },
    {
      "criterio": "tinnitus o acúfenos",
      "pregunta": "escucha zumbidos, silbidos u otros ruidos en los oidos? describa el sonido y cuando lo percibe.",
      "peso": 7
    },
    {
      "criterio": "secrecion",
      "pregunta": "presenta alguna secrecion por el oido? describa su color, consistencia y cantidad.",
      "peso": 7
    },
    {
      "criterio": "vertigo",
      "pregunta": "ha experimentado mareos o vertigo? describa la intensidad, duracion y frecuencia de los episodios.",
      "peso": 5
    },
    {
      "criterio": "cefalea",
      "pregunta": "presenta dolor de cabeza asociado a los sintomas del oido? describa la localizacion, intensidad y caracteristicas del dolor.",
      "peso": 5
    },
    {
      "criterio": "fiebre o proceso febril",
      "pregunta": "tiene fiebre? indique la temperatura corporal.",
      "peso": 6
    },
    {
      "criterio": "antecedentes",
      "pregunta": "tiene antecedentes de infecciones de oido, cirugias o traumatismos en el oido?",
      "peso": 5
    },
    {
      "criterio": "exposicion ",
      "pregunta": "se ha sumergido en agua?\nse ha introducido algun objeto al oido?\nha recibido un golpe en el oido?\nusa con frecuencia audifonos o tapones para oido?",
      "peso": 5
    }
  ],
  "arritmia cardiaca": [
    {
      "criterio": "ocupacion",
      "pregunta": "a que se dedica?",
      "peso": 8
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de arritmias cardiacas?",
      "peso": 9
    },
    {
      "criterio": "factores de riesgo",
      "pregunta": "presenta factores de riesgo cardiovascular como hipertension, diabetes, tabaquismo o dislipidemia?",
      "peso": 8
    },
    {
      "criterio": "sintomas",
      "pregunta": "que tipo de sintomas experimenta? (ej. palpitaciones, mareos, desmayos, dolor en el pecho)",
      "peso": 6
    },
    {
      "criterio": "frecuencia de los sintomas",
      "pregunta": "con que frecuencia experimenta estos sintomas?",
      "peso": 7
    },
    {
      "criterio": "duracion de los sintomas",
      "pregunta": "cuanto tiempo duran estos sintomas?",
      "peso": 7
    },
    {
      "criterio": "medicamentos",
      "pregunta": "que medicamentos esta tomando actualmente? ",
      "peso": 5
    },
    {
      "criterio": "actividad fisica",
      "pregunta": "que nivel de actividad fisica realiza?",
      "peso": 4
    }
  ],
  "enfermedades venosas": [
    {
      "criterio": "localizacion del sintoma",
      "pregunta": "donde exactamente siente el dolor o la molestia? (ej. pierna derecha, pantorrilla izquierda, etc.)",
      "peso": 8
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria el dolor? (ej. punzante, quemante, opresivo, etc.)",
      "peso": 6
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 0 al 10, siendo 0 ningun dolor y 10 el peor dolor imaginable, como calificaria su dolor?",
      "peso": 6
    },
    {
      "criterio": "factores agravantes",
      "pregunta": "que actividades o situaciones empeoran su dolor o molestia? (ej. estar de pie, caminar, sentarse, etc.)",
      "peso": 5
    },
    {
      "criterio": "factores atenuantes",
      "pregunta": "que actividades o situaciones alivian su dolor o molestia? (ej. elevar las piernas, usar medias de compresion, etc.)",
      "peso": 5
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "algun miembro de su familia ha padecido enfermedades venosas como varices, trombosis o similares?",
      "peso": 7
    },
    {
      "criterio": "historia de trombosis",
      "pregunta": "ha tenido alguna trombosis venosa profunda (tvp) previamente?",
      "peso": 7
    },
    {
      "criterio": "otros sintomas asociados",
      "pregunta": "presenta otros sintomas como hinchazon, cambios de color en la piel (enrojecimiento, oscurecimiento), endurecimiento de las piernas, ulceras en las piernas, etc.?",
      "peso": 5
    }
  ],
  "enfermedades hipertensivas": [
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existe algun antecedente familiar de hipertension arterial o enfermedades cardiovasculares?",
      "peso": 6
    },
    {
      "criterio": "factores de riesgo",
      "pregunta": "presenta el paciente obesidad, diabetes, dislipidemia, tabaquismo o sedentarismo?",
      "peso": 8
    },
    {
      "criterio": "medicion de la presion arterial",
      "pregunta": "puede proporcionar las cifras de presion arterial obtenidas en las ultimas mediciones?",
      "peso": 6
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta el paciente cefalea, mareos, disnea, epistaxis, dolor de pecho o alteraciones visuales?",
      "peso": 6
    },
    {
      "criterio": "medicacion actual",
      "pregunta": "que medicamentos esta tomando actualmente el paciente, incluyendo antihipertensivos?",
      "peso": 5
    },
    {
      "criterio": "control de la enfermedad",
      "pregunta": "con que frecuencia se realiza el paciente el control de su presion arterial y cuando fue su ultima revision medica?",
      "peso": 5
    },
    {
      "criterio": "habitos de vida",
      "pregunta": "puede describir los habitos de vida del paciente, incluyendo dieta, ejercicio fisico, consumo de alcohol y tabaco?",
      "peso": 4
    },
    {
      "criterio": "eventos cardiovasculares previos",
      "pregunta": "ha presentado el paciente eventos cardiovasculares previos como infarto de miocardio, accidente cerebrovascular o insuficiencia cardiaca?",
      "peso": 10
    }
  ],
  "enfermedades isquemicas del corazon": [
    {
      "criterio": "dolor toracico",
      "pregunta": "presenta dolor en el pecho? describa la localizacion, intensidad y caracteristicas del dolor.",
      "peso": 7
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "que actividades o situaciones desencadenan el dolor? (e.g., ejercicio, estres, reposo)",
      "peso": 5
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo dura el dolor? es constante o intermitente?",
      "peso": 5
    },
    {
      "criterio": "irradiacion del dolor",
      "pregunta": "se irradia el dolor a otras partes del cuerpo? (e.g., brazo izquierdo, mandibula, espalda)",
      "peso": 6
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta otros sintomas como sudoracion fria, nauseas, vomitos, disnea (falta de aire), mareos o palpitaciones?",
      "peso": 5
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de enfermedades cardiacas (infarto, angina de pecho, muerte subita)?",
      "peso": 6
    },
    {
      "criterio": "factores de riesgo",
      "pregunta": "presenta factores de riesgo cardiovascular como hipertension, dislipidemia (colesterol alto), diabetes, tabaquismo, obesidad o sedentarismo?\nEs primera vez que le sucede?",
      "peso": 7
    },
    {
      "criterio": "medicamentos",
      "pregunta": "que medicamentos esta tomando actualmente? incluya aspirinas, anticoagulantes, etc.",
      "peso": 4
    }
  ],
  "enfermedades del estomago o del duodeno": [
    {
      "criterio": "localizacion del dolor",
      "pregunta": "donde exactamente siente el dolor? describa la ubicacion con la mayor precision posible (p.ej., epigastrio, hipocondrio derecho, etc.).",
      "peso": 10
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria el dolor? (p.ej., ardor, punzante, colico, sordo, etc.)",
      "peso": 8
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 0 al 10, siendo 0 ningun dolor y 10 el peor dolor imaginable, como calificaria la intensidad de su dolor?",
      "peso": 7
    },
    {
      "criterio": "factores que alivian o empeoran el dolor",
      "pregunta": "hay algo que alivie o empeore su dolor? (p.ej., alimentos, medicamentos, posicion, etc.)\nFuma o toma alcohol?",
      "peso": 6
    },
    {
      "criterio": "duracion de los sintomas",
      "pregunta": "cuanto tiempo lleva experimentando estos sintomas?",
      "peso": 6
    },
    {
      "criterio": "frecuencia de los sintomas",
      "pregunta": "con que frecuencia experimenta estos sintomas? (p.ej., diario, varias veces al dia, semanalmente, etc.)",
      "peso": 6
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta otros sintomas ademas del dolor? (p.ej., nauseas, vomitos, hinchazon, eructos, perdida de peso, etc.)",
      "peso": 5
    },
    {
      "criterio": "antecedentes medicos relevantes",
      "pregunta": "tiene algun antecedente medico relevante, como ulceras pepticas, gastritis, hernia hiatal, o consumo de aines?\nse ha hecho prueba de helicobarcter pylori?",
      "peso": 5
    }
  ],
  "enfermedades del esofago": [
    {
      "criterio": "dolor",
      "pregunta": "presenta dolor en el pecho, epigastrio o espalda asociado a la ingesta de alimentos?",
      "peso": 5
    },
    {
      "criterio": "disfagia",
      "pregunta": "presenta dificultad para tragar alimentos solidos o liquidos?",
      "peso": 5
    },
    {
      "criterio": "pirosis",
      "pregunta": "experimenta sensacion de ardor en el pecho que sube hacia la garganta?",
      "peso": 5
    },
    {
      "criterio": "regurgitacion",
      "pregunta": "presenta reflujo del contenido gastrico a la boca?",
      "peso": 7
    },
    {
      "criterio": "odinofagia",
      "pregunta": "siente dolor al tragar?",
      "peso": 6
    },
    {
      "criterio": "sialorrea",
      "pregunta": "presenta aumento de saliva?",
      "peso": 6
    },
    {
      "criterio": "hematemesis",
      "pregunta": "presenta vomitos con sangre?",
      "peso": 9
    },
    {
      "criterio": "factores de riesgo",
      "pregunta": "fuma o toma alcohol?",
      "peso": 5
    }
  ],
  "digestivo bajo (intestino)": [
    {
      "criterio": "evolucion",
      "pregunta": "hace cuanto presenta los sintomas asociados al intestino?",
      "peso": 6
    },
    {
      "criterio": "frecuencia",
      "pregunta": "con que frecuencia presenta los sintomas? (ej. diario, semanal, etc.) \n",
      "peso": 7
    },
    {
      "criterio": "caracter de las heces",
      "pregunta": "como son sus heces? (ej. color, consistencia, forma)",
      "peso": 7
    },
    {
      "criterio": "acompanantes",
      "pregunta": "presenta otros sintomas acompanantes? (ej. dolor abdominal, fiebre, nauseas, vomitos)",
      "peso": 6
    },
    {
      "criterio": "factores de alivio",
      "pregunta": "hay algo que alivie sus sintomas? (ej. medicamentos, dieta, reposo)",
      "peso": 5
    },
    {
      "criterio": "factores de empeoramiento",
      "pregunta": "hay algo que empeore sus sintomas? (ej. alimentos, estres, actividad fisica)",
      "peso": 5
    },
    {
      "criterio": "antecedentes personales",
      "pregunta": "tiene antecedentes personales de enfermedades digestivas?",
      "peso": 6
    },
    {
      "criterio": "medicamentos",
      "pregunta": "que medicamentos esta tomando actualmente?",
      "peso": 5
    },
    {
      "criterio": "habitos",
      "pregunta": "como describiria su dieta?",
      "peso": 5
    }
  ],
  "enfermedades del conducto anal": [
    {
      "criterio": "localizacion del dolor",
      "pregunta": "donde exactamente siente el dolor o malestar?",
      "peso": 4
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria el dolor? (ej. punzante, quemante, sordo, etc.)",
      "peso": 5
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 1 al 10, siendo 10 el dolor mas intenso, como calificaria su dolor?",
      "peso": 4
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo lleva experimentando este dolor?",
      "peso": 8
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algo que empeore o mejore su dolor?",
      "peso": 5
    },
    {
      "criterio": "sanguimiento",
      "pregunta": "observa alguna sangre en sus heces o durante la defecacion? describa la cantidad y el color.",
      "peso": 5
    },
    {
      "criterio": "secrecion",
      "pregunta": "presenta alguna secrecion anal? describa su aspecto (ej. color, consistencia, olor).",
      "peso": 8
    },
    {
      "criterio": "cambios en los habitos intestinales",
      "pregunta": "ha notado algun cambio en sus habitos intestinales, como estrenimiento o diarrea?",
      "peso": 7
    },
    {
      "criterio": "otros sintomas",
      "pregunta": "ha notado o sentido una masa en su ano?",
      "peso": 10
    }
  ],
  "enfermedades del higado, vias biliares, pancreas": [
    {
      "criterio": "dolor abdominal",
      "pregunta": "presenta dolor abdominal? donde se localiza? como es el dolor (tipo, intensidad)?",
      "peso": 4
    },
    {
      "criterio": "ictericia",
      "pregunta": "observa coloracion amarillenta en su piel o en el blanco de sus ojos?",
      "peso": 7
    },
    {
      "criterio": "apetito",
      "pregunta": "como es su apetito en los ultimos dias o semanas?",
      "peso": 6
    },
    {
      "criterio": "nauseas y vomitos",
      "pregunta": "presenta nauseas o vomitos? con que frecuencia? que caracteristicas tienen?",
      "peso": 7
    },
    {
      "criterio": "orina y heces",
      "pregunta": "como es el color de su orina y sus heces?",
      "peso": 7
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existen antecedentes familiares de enfermedades del higado, vias biliares o pancreas?",
      "peso": 5
    },
    {
      "criterio": "consumo de alcohol",
      "pregunta": "consume alcohol? que cantidad y frecuencia?",
      "peso": 5
    },
    {
      "criterio": "medicamentos",
      "pregunta": "esta tomando algun medicamento actualmente?",
      "peso": 3
    },
    {
      "criterio": "antecedentes personales y factores de riesgo",
      "pregunta": "ha padecido de hepatitis?\nle han realizado transfusiones sanguineas?\nToma con mucha frecuencia AINES (acetaminofen, ibuprofeno, diclofenac,etc..)",
      "peso": 6
    }
  ],
  "enfermedades o trastornos del complejo bucofacial": [
    {
      "criterio": "ubicacion del dolor",
      "pregunta": "donde exactamente siente el dolor o malestar? (ej: en la mandibula, en un diente especifico, en la lengua, etc.)",
      "peso": 5
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria el dolor? (ej: agudo, punzante, sordo, constante, intermitente, etc.)",
      "peso": 6
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 0 al 10, siendo 0 ningun dolor y 10 el peor dolor imaginable, como calificaria su dolor?",
      "peso": 6
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo lleva experimentando este dolor? es constante o aparece y desaparece?",
      "peso": 5
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algo que empeore o provoque el dolor? (ej: masticar, frio, calor, tocar la zona, etc.)",
      "peso": 4
    },
    {
      "criterio": "factores atenuantes",
      "pregunta": "hay algo que alivie o disminuya el dolor? (ej: analgesicos, calor, frio, etc.)",
      "peso": 4
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta algun otro sintoma junto con el dolor? (ej: fiebre, inflamacion, dificultad para abrir la boca, alteraciones del gusto o del olfato, etc.)",
      "peso": 6
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene algun antecedente medico relevante? (ej: enfermedades previas, cirugias orales, tratamientos dentales recientes, alergias, etc.)",
      "peso": 5
    }
  ],
  "hernias": [
    {
      "criterio": "localizacion",
      "pregunta": "donde se ubica la hernia? (ejemplo: inguinal, umbilical, etc.)",
      "peso": 7
    },
    {
      "criterio": "tamano",
      "pregunta": "cual es el tamano aproximado de la hernia? (ejemplo: pequeno, mediano, grande)",
      "peso": 8
    },
    {
      "criterio": "aparicion",
      "pregunta": "cuando aparecio la hernia por primera vez? de forma subita o gradual?",
      "peso": 7
    },
    {
      "criterio": "sintomas",
      "pregunta": "presenta algun sintoma ademas de la hernia visible? (ejemplo: dolor, nauseas, vomitos, cambios en la deposicion)",
      "peso": 8
    },
    {
      "criterio": "dolor",
      "pregunta": "experimenta dolor? si es asi, describa la intensidad (escala del 1 al 10), localizacion y tipo de dolor (punzante, sordo, etc.)",
      "peso": 6
    },
    {
      "criterio": "reductibilidad",
      "pregunta": "se puede reducir la hernia manualmente? vuelve a salir?",
      "peso": 8
    },
    {
      "criterio": "actividad fisica",
      "pregunta": "que tipo de actividad fisica realiza? ha notado alguna relacion entre la actividad fisica y los sintomas de la hernia?",
      "peso": 5
    }
  ],
  "enfermedades de la mama": [
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existe algun antecedente familiar de cancer de mama o enfermedades mamarias?",
      "peso": 8
    },
    {
      "criterio": "edad de menarca",
      "pregunta": "a que edad tuvo su primera menstruacion?",
      "peso": 7
    },
    {
      "criterio": "edad de menopausia",
      "pregunta": "a que edad tuvo su ultima menstruacion?",
      "peso": 7
    },
    {
      "criterio": "numero de embarazos",
      "pregunta": "cuantos embarazos ha tenido?",
      "peso": 6
    },
    {
      "criterio": "lactancia materna",
      "pregunta": "cuanto tiempo amamanto a sus hijos?",
      "peso": 5
    },
    {
      "criterio": "uso de terapia hormonal",
      "pregunta": "ha utilizado terapia hormonal (estrogenos o progesterona)?",
      "peso": 5
    },
    {
      "criterio": "autoexamen de mamas",
      "pregunta": "con que frecuencia se realiza el autoexamen de mamas?",
      "peso": 6
    },
    {
      "criterio": "mamografia",
      "pregunta": "cuando fue su ultima mamografia?",
      "peso": 5
    }
  ],
  "enfermedades de la prostata": [
    {
      "criterio": "dolor",
      "pregunta": "presenta dolor en la zona pelvica, perineal o en la ingle?",
      "peso": 4
    },
    {
      "criterio": "miccion",
      "pregunta": "ha experimentado cambios en la frecuencia o urgencia de la miccion (orinar)?",
      "peso": 5
    },
    {
      "criterio": "flujo urinario",
      "pregunta": "ha notado algun cambio en el flujo urinario, como dificultad para iniciar la miccion, flujo debil o interrumpido?",
      "peso": 8
    },
    {
      "criterio": "goteo postmiccional",
      "pregunta": "experimenta goteo de orina despues de terminar de orinar?",
      "peso": 8
    },
    {
      "criterio": "nocturia",
      "pregunta": "se despierta por la noche para orinar con mas frecuencia de lo habitual?",
      "peso": 7
    },
    {
      "criterio": "hematuria",
      "pregunta": "ha observado sangre en la orina?",
      "peso": 6
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de cancer de prostata u otras enfermedades prostaticas?",
      "peso": 7
    },
    {
      "criterio": "funcion sexual",
      "pregunta": "ha experimentado algun cambio en su funcion sexual, como disfuncion erectil o disminucion del deseo sexual?",
      "peso": 5
    }
  ],
  "enfermedades de la vejiga o las vias urinarias": [
    {
      "criterio": "dolor",
      "pregunta": "presenta dolor al orinar o en la zona de la vejiga?",
      "peso": 3
    },
    {
      "criterio": "frecuencia urinaria",
      "pregunta": "con que frecuencia orina al dia? ha notado algun cambio en la frecuencia?",
      "peso": 4
    },
    {
      "criterio": "urgencia urinaria",
      "pregunta": "experimenta urgencia o necesidad imperiosa de orinar?",
      "peso": 5
    },
    {
      "criterio": "nicturia",
      "pregunta": "se despierta por la noche para orinar?",
      "peso": 5
    },
    {
      "criterio": "incontinencia",
      "pregunta": "presenta incontinencia urinaria (perdida involuntaria de orina)?",
      "peso": 9
    },
    {
      "criterio": "color y olor de la orina",
      "pregunta": "como describiria el color y el olor de su orina? ha notado algun cambio?",
      "peso": 6
    },
    {
      "criterio": "Dolor al Orinar ",
      "pregunta": "Ha presentado dolor al orinar o ardor al orinar ",
      "peso": 6
    },
    {
      "criterio": "medicamentos",
      "pregunta": "esta tomando algun medicamento actualmente? puede listarlos?",
      "peso": 3
    }
  ],
  "enfermedades del riñon": [
    {
      "criterio": "dolor",
      "pregunta": "siente dolor en la zona lumbar o en los costados?",
      "peso": 5
    },
    {
      "criterio": "frecuencia urinaria",
      "pregunta": "ha notado cambios en la frecuencia con la que orina? mas o menos frecuente?",
      "peso": 6
    },
    {
      "criterio": "cambios en el color de la orina",
      "pregunta": "ha notado algun cambio en el color de su orina? (ej. mas oscura, rojiza, espumosa)",
      "peso": 6
    },
    {
      "criterio": "hinchazon",
      "pregunta": "experimenta hinchazon en las piernas, tobillos o pies?",
      "peso": 7
    },
    {
      "criterio": "presion arterial",
      "pregunta": "conoce su presion arterial? ha tenido mediciones altas recientemente?",
      "peso": 6
    },
    {
      "criterio": "fatiga",
      "pregunta": "se siente mas cansado o fatigado de lo normal?",
      "peso": 6
    },
    {
      "criterio": "nauseas o vomitos",
      "pregunta": "ha experimentado nauseas o vomitos recientemente?",
      "peso": 6
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de enfermedades renales?",
      "peso": 8
    },
    {
      "criterio": "antecedentes personales",
      "pregunta": "Padece de la presión arterial o de diabetes mellitus ",
      "peso": 6
    }
  ],
  "enfermedades inflamatorias pelvicas femeninas": [
    {
      "criterio": "localizacion del dolor",
      "pregunta": "donde exactamente siente el dolor? (describa la localizacion con precision, por ejemplo, lado derecho de la pelvis, bajo vientre, etc.)",
      "peso": 4
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria su dolor? (por ejemplo, punzante, sordo, colico, ardor, etc.)",
      "peso": 5
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 0 al 10, siendo 0 ningun dolor y 10 el peor dolor imaginable, como calificaria la intensidad de su dolor?",
      "peso": 7
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo lleva experimentando este dolor?",
      "peso": 7
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay alguna actividad, posicion o situacion que empeore o provoque el dolor?",
      "peso": 3
    },
    {
      "criterio": "flujo menstrual",
      "pregunta": "como describiria su flujo menstrual? (cantidad, color, duracion, etc.) ha notado algun cambio en su flujo menstrual recientemente?",
      "peso": 5
    },
    {
      "criterio": "antecedentes ginecologicos",
      "pregunta": "ha tenido alguna enfermedad inflamatoria pelvica previamente? ha tenido alguna cirugia pelvica? tiene algun otro problema ginecologico?",
      "peso": 4
    }
  ],
  "infecciones de transmision sexual": [
    {
      "criterio": "tiempo de incubacion",
      "pregunta": "cuanto tiempo ha transcurrido desde la posible exposicion hasta la aparicion de los sintomas?",
      "peso": 4
    },
    {
      "criterio": "sintomas",
      "pregunta": "que sintomas presenta? (ej: flujo vaginal, lesiones genitales, dolor al orinar, etc.)",
      "peso": 6
    },
    {
      "criterio": "conducta sexual",
      "pregunta": "puede describir sus practicas sexuales recientes, incluyendo el numero de parejas y el uso de proteccion?",
      "peso": 7
    },
    {
      "criterio": "contacto con otras personas",
      "pregunta": "ha tenido practicas sexuales de reisgo en los últimos 6 meses?",
      "peso": 9
    },
    {
      "criterio": "uso de anticonceptivos",
      "pregunta": "que tipo de anticonceptivos utiliza? usa condon en todas sus practicas sexuales?",
      "peso": 4
    },
    {
      "criterio": "medicamentos",
      "pregunta": "esta tomando algun medicamento actualmente?",
      "peso": 3
    }
  ],
  "trastornos de sangrado menstruales o no menstruales": [
    {
      "criterio": "localizacion del sangrado",
      "pregunta": "donde se localiza el sangrado? (vagina, recto, etc.)",
      "peso": 6
    },
    {
      "criterio": "duracion del sangrado",
      "pregunta": "cuanto tiempo lleva sangrando?",
      "peso": 4
    },
    {
      "criterio": "cantidad del sangrado",
      "pregunta": "cuanta sangre ha perdido? (estime con toallas sanitarias o compresas utilizadas)",
      "peso": 7
    },
    {
      "criterio": "frecuencia del sangrado",
      "pregunta": "con que frecuencia sangra? (diario, semanal, etc.)",
      "peso": 5
    },
    {
      "criterio": "acompanamiento de otros sintomas",
      "pregunta": "presenta otros sintomas como dolor, mareos, debilidad, etc.?",
      "peso": 6
    },
    {
      "criterio": "medicamentos",
      "pregunta": "esta tomando algun medicamento que pueda estar relacionado con el sangrado (anticoagulantes, aspirina, etc.)?",
      "peso": 5
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene antecedentes de trastornos de coagulacion, enfermedades hepaticas o renales, o cirugias recientes?",
      "peso": 6
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de trastornos hemorragicos?",
      "peso": 5
    }
  ],
  "trastornos genitales femeninos externos": [
    {
      "criterio": "localizacion del sintoma",
      "pregunta": "donde exactamente se localiza el sintoma o molestia? (describa la zona afectada con la mayor precision posible, utilizando referencias anatomicas si es necesario.)",
      "peso": 6
    },
    {
      "criterio": "tipo de sintoma",
      "pregunta": "que tipo de sintoma experimenta? (por ejemplo: dolor, picor, ardor, flujo inusual, bulto, lesion, etc.)",
      "peso": 7
    },
    {
      "criterio": "caracteristicas del sintoma",
      "pregunta": "puede describir las caracteristicas del sintoma? (por ejemplo: intensidad del dolor en una escala de 0-10, tipo de dolor (punzante, quemante, sordo), duracion, etc.)",
      "peso": 6
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algun factor que empeore o desencadene el sintoma? (por ejemplo: actividad fisica, posicion corporal, relaciones sexuales, uso de productos especificos, etc.)",
      "peso": 4
    },
    {
      "criterio": "factores atenuantes",
      "pregunta": "hay algun factor que mejore o disminuya el sintoma? (por ejemplo: reposo, medicamentos, aplicacion de cremas, etc.)",
      "peso": 4
    },
    {
      "criterio": "antecedentes medicos relevantes",
      "pregunta": "tiene antecedentes medicos relevantes, como enfermedades de transmision sexual, alergias, cirugias previas en la zona, o tratamientos hormonales?",
      "peso": 5
    },
    {
      "criterio": "medicamentos actuales",
      "pregunta": "que medicamentos esta tomando actualmente, incluyendo vitaminas, suplementos y remedios herbales?",
      "peso": 2
    },
    {
      "criterio": "habitos higienicos",
      "pregunta": "puede describir sus habitos de higiene intima? (por ejemplo, frecuencia de lavado, productos utilizados, etc.)",
      "peso": 6
    }
  ],
  "trastornos genitales masculinos": [
    {
      "criterio": "dolor",
      "pregunta": "siente dolor en sus genitales? describa el tipo de dolor (quemante, punzante, etc.), la intensidad (en una escala de 1 a 10) y la localizacion.",
      "peso": 5
    },
    {
      "criterio": "secrecion",
      "pregunta": "presenta alguna secrecion por el pene o el escroto? describa el color, la consistencia, el olor y la cantidad.",
      "peso": 6
    },
    {
      "criterio": "lesiones",
      "pregunta": "tiene alguna lesion en sus genitales? describa su apariencia (tamano, color, forma), si le causan dolor o molestias y cuando aparecieron.",
      "peso": 8
    },
    {
      "criterio": "inflamacion",
      "pregunta": "observa alguna inflamacion en sus genitales, como enrojecimiento o hinchazon? indique la localizacion y si le produce molestia.",
      "peso": 7
    },
    {
      "criterio": "miccion",
      "pregunta": "tiene dificultad para orinar? describa la frecuencia, la intensidad y si presenta dolor al orinar.",
      "peso": 6
    },
    {
      "criterio": "funcion sexual",
      "pregunta": "ha experimentado algun cambio en su funcion sexual, como disfuncion erectil o disminucion de la libido?",
      "peso": 5
    },
    {
      "criterio": "antecedentes",
      "pregunta": "tiene antecedentes de enfermedades de transmision sexual, cirugias en la zona genital o alergias?",
      "peso": 5
    }
  ],
  "trastornos menopausicos o perimenopausicos": [
    {
      "criterio": "edad de inicio",
      "pregunta": "a que edad comenzaron los sintomas relacionados con la menopausia o perimenopausia?",
      "peso": 6
    },
    {
      "criterio": "duracion de los sintomas",
      "pregunta": "cuanto tiempo lleva experimentando estos sintomas?",
      "peso": 4
    },
    {
      "criterio": "frecuencia de los sintomas",
      "pregunta": "con que frecuencia experimenta cada uno de los sintomas (ej: sofocos, sudoracion nocturna, etc.)?",
      "peso": 6
    },
    {
      "criterio": "intensidad de los sintomas",
      "pregunta": "que tan intensos son sus sintomas en una escala del 1 al 10, siendo 10 el mas intenso?",
      "peso": 4
    },
    {
      "criterio": "impacto en la calidad de vida",
      "pregunta": "como afectan estos sintomas a su vida diaria, trabajo, relaciones sociales y sueno?",
      "peso": 5
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de trastornos menopausicos o perimenopausicos?",
      "peso": 5
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tratamiento previamente para estos sintomas? si es asi, cual fue y cual fue la respuesta?",
      "peso": 4
    },
    {
      "criterio": "otros sintomas asociados",
      "pregunta": "experimenta otros sintomas ademas de los mencionados, como cambios en el estado de animo, problemas de sueno, cambios en la libido, sequedad vaginal, etc.?",
      "peso": 7
    }
  ],
  "enfermedades del sistema musculo esqueletico o del tejido conjuntivo": [
    {
      "criterio": "localizacion del dolor",
      "pregunta": "donde exactamente siente el dolor? por favor, sea lo mas especifico posible (ej., lado derecho de la rodilla, parte inferior de la espalda, etc.)",
      "peso": 7
    },
    {
      "criterio": "tipo de dolor",
      "pregunta": "como describiria su dolor? (ej., agudo, sordo, punzante, quemante, etc.)",
      "peso": 6
    },
    {
      "criterio": "intensidad del dolor",
      "pregunta": "en una escala del 0 al 10, siendo 0 ningun dolor y 10 el peor dolor imaginable, como calificaria su dolor?",
      "peso": 7
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo lleva experimentando este dolor?",
      "peso": 6
    },
    {
      "criterio": "factores agravantes",
      "pregunta": "que actividades o situaciones empeoran su dolor?",
      "peso": 4
    },
    {
      "criterio": "factores atenuantes",
      "pregunta": "que actividades o situaciones alivian su dolor?",
      "peso": 4
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta algun otro sintoma ademas del dolor? (ej., hinchazon, enrojecimiento, rigidez, limitacion del movimiento, etc.)",
      "peso": 6
    },
    {
      "criterio": "antecedentes medicos relevantes",
      "pregunta": "tiene algun antecedente medico relevante que pueda estar relacionado con su dolor? (ej., artritis, lesiones previas, etc.)",
      "peso": 5
    }
  ],
  "cefalea y migrana": [
    {
      "criterio": "localizacion",
      "pregunta": "donde exactamente siente el dolor de cabeza?",
      "peso": 6
    },
    {
      "criterio": "intensidad",
      "pregunta": "en una escala del 1 al 10, siendo 10 el dolor mas intenso, como calificaria su dolor de cabeza?",
      "peso": 8
    },
    {
      "criterio": "duracion",
      "pregunta": "cuanto tiempo dura cada episodio de dolor de cabeza?",
      "peso": 5
    },
    {
      "criterio": "frecuencia",
      "pregunta": "con que frecuencia experimenta estos dolores de cabeza (por ejemplo, diariamente, semanalmente, mensualmente)?",
      "peso": 7
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algo que desencadene sus dolores de cabeza (por ejemplo, estres, alimentos, cambios hormonales, falta de sueno)?",
      "peso": 6
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta otros sintomas junto con el dolor de cabeza (por ejemplo, nauseas, vomitos, sensibilidad a la luz o al sonido, vision borrosa)?",
      "peso": 7
    },
    {
      "criterio": "medicamentos",
      "pregunta": "que medicamentos esta tomando actualmente, incluyendo analgesicos y medicamentos de venta libre?",
      "peso": 4
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "alguien en su familia tiene antecedentes de migranas o dolores de cabeza severos?",
      "peso": 5
    }
  ],
  "neuritis y neuralgias": [
    {
      "criterio": "ubicacion del dolor",
      "pregunta": "donde exactamente siente el dolor? por favor, sea lo mas preciso posible, indicando si el dolor se irradia a otras zonas.",
      "peso": 8
    },
    {
      "criterio": "caracteristicas del dolor",
      "pregunta": "como describiria su dolor? (ej. punzante, quemante, urente, etc.) es constante o intermitente? cual es su intensidad en una escala de 0 a 10, siendo 0 ningun dolor y 10 el dolor mas intenso imaginable?",
      "peso": 7
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay alguna actividad, posicion o situacion que empeore su dolor?",
      "peso": 5
    },
    {
      "criterio": "factores atenuantes",
      "pregunta": "hay algo que alivie su dolor? (ej. medicamentos, reposo, calor, frio)",
      "peso": 5
    },
    {
      "criterio": "duracion del dolor",
      "pregunta": "cuanto tiempo lleva sintiendo este dolor?",
      "peso": 6
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene algun antecedente medico relevante, como enfermedades previas, cirugias o traumatismos?",
      "peso": 5
    },
    {
      "criterio": "medicamentos actuales",
      "pregunta": "que medicamentos esta tomando actualmente, incluyendo suplementos vitaminicos o hierbas?",
      "peso": 4
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "experimenta otros sintomas junto con el dolor, como debilidad muscular, entumecimiento, hormigueo, cambios en la sensibilidad o alteraciones en la funcion de alguna zona del cuerpo?",
      "peso": 7
    }
  ],
  "vias respiratorias superiores": [
    {
      "criterio": "sintomas",
      "pregunta": "que sintomas presenta en las vias respiratorias ejemplo: tos, dolor de garganta, congestion nasal",
      "peso": 6
    },
    {
      "criterio": "duracion",
      "pregunta": "cuanto tiempo lleva presentando estos sintomas?",
      "peso": 4
    },
    {
      "criterio": "intensidad",
      "pregunta": "que tan intensos son los sintomas? (ej. leve, moderado, severo)",
      "peso": 5
    },
    {
      "criterio": "factores que alivian o agravan los síntomas",
      "pregunta": "hay algun factor que empeore sus sintomas? (ej. humo, alergenos, cambios climaticos)",
      "peso": 6
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene antecedentes de enfermedades respiratorias? (ej. asma, alergias, etc.)",
      "peso": 7
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tratamiento previamente para estos sintomas? si es asi, cual?",
      "peso": 4
    },
    {
      "criterio": "medicamentos actuales",
      "pregunta": "esta tomando algun medicamento actualmente?",
      "peso": 3
    },
    {
      "criterio": "otros sintomas",
      "pregunta": "presenta otros sintomas asociados, como fiebre, dolor de cabeza, malestar general?",
      "peso": 5
    }
  ],
  "enfermedades del ojo, parpado, conjuntivas y vias lagrimales": [
    {
      "criterio": "ojo afectado",
      "pregunta": "que ojo esta afectado? (derecho, izquierdo o ambos)",
      "peso": 5
    },
    {
      "criterio": "inicio de los sintomas",
      "pregunta": "cuando comenzaron los sintomas? (fecha aproximada)\ncomo le inicio?",
      "peso": 4
    },
    {
      "criterio": "tipo de sintoma principal",
      "pregunta": "cual es el sintoma principal? (dolor, enrojecimiento, vision borrosa, lagrimeo excesivo, etc.)\nHa notado masa o salida de secreciones?",
      "peso": 6
    },
    {
      "criterio": "severidad del sintoma",
      "pregunta": "que tan severo es el sintoma principal? (leve, moderado, severo)\n",
      "peso": 5
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algun factor que empeore los sintomas? (luz, frotamiento, alergenos, etc.)",
      "peso": 5
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene antecedentes de enfermedades oculares, alergias o alguna condicion medica relevante?\nusa anteojos?",
      "peso": 6
    },
    {
      "criterio": "medicamentos actuales",
      "pregunta": "que medicamentos esta tomando actualmente (incluyendo gotas oculares, vitaminas, etc.)?",
      "peso": 3
    },
    {
      "criterio": "exposicion a sustancias",
      "pregunta": "ha estado expuesto a sustancias irritantes o quimicas (como humo, polvo, quimicos industriales, etc.)?",
      "peso": 7
    }
  ],
  "diabetes": [
    {
      "criterio": "sintomas",
      "pregunta": "Que sintomas presenta relacionados con la diabetes, como poliuria, polidipsia, polifagia, perdida de peso o vision borrosa? ",
      "peso": 8
    },
    {
      "criterio": "duracion",
      "pregunta": "cuanto tiempo lleva presentando estos sintomas?\nEs primera vez que presenta estos sintomas o ha sucedido anteriormente?",
      "peso": 6
    },
    {
      "criterio": "control glucemico",
      "pregunta": "se realiza un control regular de su glucemia? con que frecuencia y cuales son los valores obtenidos?\nPosee glucometro en casa?",
      "peso": 7
    },
    {
      "criterio": "tratamiento actual",
      "pregunta": "que tratamiento recibe actualmente para la diabetes (medicamentos, insulina, dieta, ejercicio)?",
      "peso": 7
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "Existe algun antecedente familiar de diabetes?\nExite antecedentes de sobrepeso u obesidad en su familia?",
      "peso": 8
    },
    {
      "criterio": "comorbilidades",
      "pregunta": "presenta alguna otra enfermedad o condicion medica, como hipertension arterial, enfermedad cardiovascular o dislipidemia?",
      "peso": 7
    },
    {
      "criterio": "habitos de vida",
      "pregunta": "puede describir sus habitos de vida, incluyendo su dieta, actividad fisica y consumo de tabaco y alcohol?",
      "peso": 7
    },
    {
      "criterio": "eventos agudos",
      "pregunta": "ha presentado algun evento agudo recientemente, como cetoacidosis diabetica o hipoglucemia severa?\nHa estado ingresado por alguna complicacion aguda?",
      "peso": 7
    }
  ],
  "sobrepeso u obesidad": [
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existe algun antecedente familiar de sobrepeso u obesidad?",
      "peso": 6
    },
    {
      "criterio": "habitos alimenticios",
      "pregunta": "puede describir sus habitos alimenticios, incluyendo el tamano de las porciones, frecuencia de comidas y tipos de alimentos consumidos?\nCon que frecuencia consume comida rapida?\n",
      "peso": 8
    },
    {
      "criterio": "actividad fisica",
      "pregunta": "que tipo y cuanta actividad fisica realiza regularmente?\nCon que frecuencia realiza actividad fisica?",
      "peso": 6
    },
    {
      "criterio": "medicamentos",
      "pregunta": "esta tomando algun medicamento que pueda contribuir al aumento de peso?   \nToma anticonceptivos o antidepresivo?",
      "peso": 6
    },
    {
      "criterio": "sueno",
      "pregunta": "cuantas horas de sueno obtiene por noche?",
      "peso": 5
    },
    {
      "criterio": "estres",
      "pregunta": "como describiria sus niveles de estres?",
      "peso": 6
    },
    {
      "criterio": "indice de masa corporal (imc)",
      "pregunta": "conoce su peso y talla? indice de masa corporal (imc)?",
      "peso": 8
    },
    {
      "criterio": "cambios de peso recientes",
      "pregunta": "ha experimentado algun cambio significativo en su peso recientemente?\nCuando fue la ultima vez que se peso y cuanto fue el valor?",
      "peso": 4
    }
  ],
  "trastornos mentales, del comportamiento y del neurodesarrollo": [
    {
      "criterio": "inicio de los sintomas",
      "pregunta": "cuando comenzaron los sintomas que le preocupan?",
      "peso": 4
    },
    {
      "criterio": "frecuencia de los sintomas",
      "pregunta": "Es la primera vez que ha experimentado estos sintomas? ",
      "peso": 5
    },
    {
      "criterio": "impacto en la vida diaria",
      "pregunta": "como afectan estos sintomas a su vida diaria, trabajo, relaciones sociales o actividades cotidianas?",
      "peso": 7
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algo que parezca empeorar o mejorar sus sintomas?",
      "peso": 4
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "alguien en su familia ha presentado problemas similares?",
      "peso": 7
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tratamiento anteriormente para estos sintomas? ",
      "peso": 6
    }
  ],
  "enfermedades del pulmon": [
    {
      "criterio": "tos",
      "pregunta": "presenta tos? de ser asi, describa su caracteristica (seca, productiva, con flemas, etc.) y su duracion.",
      "peso": 8
    },
    {
      "criterio": "disnea",
      "pregunta": "presenta dificultad para respirar? a que nivel de esfuerzo se presenta? (en reposo, al caminar, al subir escaleras, etc.)",
      "peso": 6
    },
    {
      "criterio": "expectoracion",
      "pregunta": "si presenta tos productiva, describa el color, la cantidad y la consistencia de la expectoracion.",
      "peso": 5
    },
    {
      "criterio": "dolor toracico",
      "pregunta": "presenta dolor en el pecho? describa su localizacion, intensidad y caracteristicas (opresion, punzada, etc.).",
      "peso": 5
    },
    {
      "criterio": "fiebre",
      "pregunta": "presenta fiebre? cual es su temperatura maxima?",
      "peso": 5
    },
    {
      "criterio": "antecedentes de enfermedades respiratorias",
      "pregunta": "ha padecido anteriormente alguna enfermedad respiratoria (asma, bronquitis, neumonia, tuberculosis, etc.)?",
      "peso": 6
    },
    {
      "criterio": "habitos toxicos",
      "pregunta": "fuma? cuantos cigarrillos fuma al dia? consume alcohol? consume drogas?",
      "peso": 5
    },
    {
      "criterio": "ocupacion y ambiente laboral",
      "pregunta": "cual es su ocupacion? esta expuesto a algun tipo de polvo, humo o gases en su lugar de trabajo?",
      "peso": 5
    }
  ],
  "vias respiratorias bajas": [
    {
      "criterio": "sintomas respiratorios",
      "pregunta": "que tipo de sintomas respiratorios presenta? (tos, disnea, expectoracion, dolor toracico, etc.)",
      "peso": 7
    },
    {
      "criterio": "duracion de los sintomas",
      "pregunta": "cuanto tiempo lleva presentando estos sintomas?",
      "peso": 5
    },
    {
      "criterio": "severidad de los sintomas",
      "pregunta": "que tan intensos son sus sintomas? (leve, moderado, grave)",
      "peso": 6
    },
    {
      "criterio": "factores desencadenantes",
      "pregunta": "hay algun factor que empeore sus sintomas? (ejercicio fisico, alergenos, cambios climaticos, etc.)",
      "peso": 4
    },
    {
      "criterio": "antecedentes medicos",
      "pregunta": "tiene algun antecedente medico relevante? (asma, epoc, alergias, tabaquismo, etc.)",
      "peso": 5
    },
    {
      "criterio": "medicamentos",
      "pregunta": "que medicamentos esta tomando actualmente?",
      "peso": 3
    },
    {
      "criterio": "exposicion a agentes infecciosos",
      "pregunta": "ha estado expuesto a alguna persona con sintomas respiratorios o a ambientes con alto nivel de contaminacion?",
      "peso": 4
    },
    {
      "criterio": "vacunacion",
      "pregunta": "esta vacunado contra la influenza o el neumococo?",
      "peso": 3
    }
  ],
  "tumores de la piel y tcs": [
    {
      "criterio": "localizacion",
      "pregunta": "donde se encuentra el tumor o la lesion?",
      "peso": 7
    },
    {
      "criterio": "tamano",
      "pregunta": "cual es el tamano aproximado del tumor o la lesion?",
      "peso": 8
    },
    {
      "criterio": "forma",
      "pregunta": "como describiria la forma del tumor o la lesion? (ej. redonda, ovalada, irregular)",
      "peso": 7
    },
    {
      "criterio": "color",
      "pregunta": "de que color es el tumor o la lesion?",
      "peso": 5
    },
    {
      "criterio": "superficie",
      "pregunta": "como es la superficie del tumor o la lesion? (ej. lisa, rugosa, ulcerada)",
      "peso": 6
    },
    {
      "criterio": "evolucion",
      "pregunta": "cuanto tiempo lleva presente el tumor o la lesion? ha cambiado de tamano o aspecto?",
      "peso": 7
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta algun sintoma asociado como dolor, picor, sangrado o secrecion?",
      "peso": 6
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de cancer de piel o de tumores similares?",
      "peso": 8
    }
  ],
  "tumores genitales femeninos": [
    {
      "criterio": "localizacion",
      "pregunta": "donde se encuentra el tumor? (ej. labios mayores, labios menores, clitoris, vagina, cuello uterino)",
      "peso": 6
    },
    {
      "criterio": "tamano",
      "pregunta": "cual es el tamano aproximado del tumor? (ej. diametro en centimetros o relacion con estructuras anatomicas)",
      "peso": 7
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta sangrado vaginal, flujo anormal, dolor pelvico, dispareunia (dolor durante las relaciones sexuales), cambios en la miccion o defecacion?",
      "peso": 7
    },
    {
      "criterio": "duracion de los sintomas",
      "pregunta": "cuanto tiempo lleva presentando estos sintomas?",
      "peso": 6
    },
    {
      "criterio": "antecedentes ginecologicos",
      "pregunta": "tiene antecedentes de enfermedades ginecologicas, infecciones de transmision sexual, embarazos, abortos o partos?",
      "peso": 8
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de cancer u otras enfermedades ginecologicas?",
      "peso": 9
    },
    {
      "criterio": "habitos",
      "pregunta": "consume tabaco o alcohol? tiene sobrepeso u obesidad?",
      "peso": 5
    },
    {
      "criterio": "metodos anticonceptivos",
      "pregunta": "que metodos anticonceptivos ha utilizado?",
      "peso": 6
    }
  ],
  "sintomas generales": [
    {
      "criterio": "fecha de inicio",
      "pregunta": "¿cuál es la fecha de inicio de los síntomas?",
      "peso": 7
    },
    {
      "criterio": "localización",
      "pregunta": "¿cuál es la ubicación específica de los síntomas?",
      "peso": 8
    },
    {
      "criterio": "duración",
      "pregunta": "¿cuánto tiempo han estado estos síntomas presentes?",
      "peso": 9
    },
    {
      "criterio": "caracterización",
      "pregunta": "¿cómo describe el paciente estos síntomas?",
      "peso": 6
    },
    {
      "criterio": "factores que alivian o agravan",
      "pregunta": "¿hay algo que alivie o agrave el síntoma?",
      "peso": 5
    },
    {
      "criterio": "irradiación",
      "pregunta": "¿se irradia o se extiende a otras partes del cuerpo?",
      "peso": 4
    },
    {
      "criterio": "factor temporal",
      "pregunta": "¿estos síntomas se alivian o agravan a cierta hora del día?",
      "peso": 4
    },
    {
      "criterio": "severidad",
      "pregunta": "usando una escala del 1 al 10, siendo 1 el menos grave y 10 el peor, ¿cómo califica el paciente sus síntomas?",
      "peso": 7
    }
  ],
  "tumores malignos": [
    {
      "criterio": "localizacion del tumor",
      "pregunta": "en que parte del cuerpo se encuentra el tumor?",
      "peso": 7
    },
    {
      "criterio": "tamano del tumor",
      "pregunta": "cual es el tamano aproximado del tumor?",
      "peso": 7
    },
    {
      "criterio": "metastasis",
      "pregunta": "se ha detectado la presencia de metastasis?",
      "peso": 6
    },
    {
      "criterio": "sintomas",
      "pregunta": "que sintomas presenta el paciente relacionados con el tumor?",
      "peso": 5
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "existe algun antecedente familiar de tumores malignos?",
      "peso": 7
    },
    {
      "criterio": "habitos toxicos",
      "pregunta": "el paciente presenta habitos toxicos como tabaquismo o alcoholismo?",
      "peso": 5
    },
    {
      "criterio": "estudios previos",
      "pregunta": "se han realizado estudios previos como biopsias o imagenes medicas?",
      "peso": 6
    },
    {
      "criterio": "tratamiento previo",
      "pregunta": "ha recibido algun tratamiento previo para el tumor?",
      "peso": 6
    }
  ],
  "tumores mama": [
    {
      "criterio": "localizacion",
      "pregunta": "en que cuadrante de la mama se encuentra la masa o el bulto?",
      "peso": 8
    },
    {
      "criterio": "tamano",
      "pregunta": "cual es el tamano aproximado del bulto o la masa? (por ejemplo, diametro en centimetros)",
      "peso": 6
    },
    {
      "criterio": "consistencia",
      "pregunta": "como es la consistencia del bulto o la masa? (por ejemplo, duro, blando, firme)",
      "peso": 7
    },
    {
      "criterio": "movilidad",
      "pregunta": "es movil o esta fijo el bulto o la masa a la piel o a los tejidos subyacentes?",
      "peso": 6
    },
    {
      "criterio": "aspecto de la piel",
      "pregunta": "hay cambios en la piel sobre el bulto o la masa? (por ejemplo, enrojecimiento, retraccion, ulceracion)",
      "peso": 7
    },
    {
      "criterio": "adenopatias",
      "pregunta": "presenta inflamacion o ganglios linfaticos en las axilas u otras zonas cercanas?",
      "peso": 5
    },
    {
      "criterio": "antecedentes familiares",
      "pregunta": "hay antecedentes familiares de cancer de mama?",
      "peso": 7
    },
    {
      "criterio": "sintomas asociados",
      "pregunta": "presenta otros sintomas asociados, como dolor, cambios en el pezon o secrecion mamaria?",
      "peso": 6
    }
  ]
}


SINTOMAS_POR_AREA = {
    "alergia y trastornos inmunitarios": [
        "alergia en la piel",
        "aumento de la sensibilidad al ruido",
        "congestión o escurrimiento nasal desencadenados por el ambiente",
        "contacto con alergeno",
        "estornudos por alergia",
        "picazon",
        "ronchas en la piel",
    ],
    "embarazo que finaliza en aborto": [
        "aborto médico en el último mes",
        "sangrado vaginal diferente al de la menstruación",
        "dolor al amamantar",
        "aumento de peso",
    ],
    "complicaciones relacionadas con el puerperio": [
        "aborto médico en el último mes",
        "aumento de peso",
        "dolor al amamantar",
        "cambios en el pezón",
        "pezon inflamado",
        "sangrado vaginal diferente al de la menstruación",
        "parto reciente",
        "pérdida de peso",
        "depresión",
        "ansiedad",
        "malestar general",
        "fatiga",
        "palpitaciones",
        "insomnio",
    ],
    "trastornos del embarazo y parto": [
        "aborto médico en el último mes",
        "dolor al amamantar",
        "embarazo",
        "parto reciente",
        "período atrasado",
        "período irregular",
        "sangrado menstrual abundante",
        "sangrado vaginal diferente al de la menstruación",
    ],
    "enfermedades de la sangre o de los organos hematopoyeticos": [
        "antecedente familiar de trastornos de la coagulación",
        "antecedente de trombosis",
        "sangrado que no se detiene",
        "sangrado menstrual abundante",
        "heces con sangre",
        "moretón después de una lesión",
        "palidez de la piel",
    ],
    "enfermedades del oído o de la apófisis mastoides": [
        "pérdida de audición",
        "oído taponado",
        "dolor de oídos",
        "dolor en zona de la oreja",
        "secreción por el oído",
        "zumbido en los oídos",
        "sordera de intensidad y duración variables",
        "sordera progresiva sin fluctuar",
        "sordera repentina",
        "sonidos pulsátiles en mis oídos",
        "tirar o jalar de su propia oreja",
    ],
    "arritmia cardiaca": [
        "palpitaciones",
        "ritmo cardíaco acelerado",
        "dolor de pecho intenso y opresivo",
        "dolor de pecho intenso irradiado a brazo izquierdo",
        "dolor de pecho intenso irradiado a cuello",
        "dolor de pecho leve o moderado, no se irradia",
    ],
    "enfermedades venosas": [
        "vena agrandada de miembro inferior",
        "hinchazón de cualquier extremidad inferior",
        "pierna hinchada",
    ],
    "enfermedades hipertensivas": [
        "antecedentes de presión arterial alta",
        "hipertensión diagnosticada",
        "subida repentina de la presión arterial",
        "bajón de presión arterial",
    ],
    "enfermedades isquemicas del corazon": [
        "dolor de pecho intenso irradiado a brazo izquierdo",
        "dolor de pecho intenso irradiado a cuello",
        "dolor de pecho intenso y opresivo",
        "dolor de pecho leve o moderado, no se irradia",
        "antecedente de infarto",
        "enfermedad coronaria diagnosticada",
        "falta de aire al hacer mediano esfuerzo",
        "falta de aire al hacer pequeño esfuerzo",
        "palpitaciones",
        "ritmo cardíaco acelerado",
        "cansancio respiratorio",
        "bajón de presión arterial",
        "subida repentina de la presión arterial",
        "hipertensión diagnosticada",
        "colesterol alto",
        "asma diagnosticado",
        "crisis de asma",
        "dificultad para respirar al hacer mucho esfuerzo",
        "dificultad para respirar al hacer pequeño esfuerzo",
        "dificultad para respirar durante el sueño",
        "dificultad para respirar en la noche",
    ],
    "enfermedades del estomago o del duodeno": [
        "acidez",
        "apetito disminuido",
        "ardor de garganta",
        "ardor en los ojos",
        "dolor abdominal intenso",
        "dolor abdominal que va y viene",
        "dolor de estómago intenso",
        "dolor de estómago que va y viene",
        "diarrea más de 6 veces diarias",
        "diarrea menos de 6 veces diarias",
        "dificultad al tragar",
        "eructar",
        "estómago",
        "heces con sangre",
        "heces negras",
        "heces rojas",
        "indigestión",
        "náuseas",
        "úlceras gástricas recurrentes",
        "vómito",
        "vómito con sangre",
    ],
    "enfermedades del esofago": [
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad habitual para tragar",
        "dolor al tragar",
        "dificultad repentina para tragar",
        "sensación de nudo en la garganta",
        "ardor de garganta",
    ],
    "digestivo bajo (intestino)": [
        "dolor abdominal intenso",
        "dolor abdominal que va y viene",
        "diarrea más de 6 veces diarias",
        "diarrea menos de 6 veces diarias",
        "heces con grasa",
        "heces con sangre",
        "heces finas",
        "heces malolientes",
        "heces negras",
        "heces rojas",
        "dolor al defecar",
        "estreñimiento",
    ],
    "enfermedades del conducto anal": [
        "dolor al defecar",
        "dolor en el ano",
        "sangrado por el ano",
        "llagas o absceso cerca del ano",
    ],
    "enfermedades del higado, vias biliares, pancreas": [
        "abdomen aumentado de tamaño",
        "apetito disminuido",
        "heces con grasa",
        "ictericia",
        "piel amarilla repentina o ictericia",
        "dolor abdominal intenso",
        "dolor abdominal que va y viene",
        "náuseas",
        "vómitos",
    ],
    "enfermedades o trastornos del complejo bucofacial": [
        "alteración o pérdida del gusto",
        "ampolla de leche en el pezón",
        "ardor de garganta",
        "ardor en los ojos",
        "arrugas o formación de agujeros en la piel de los pechos",
        "cambio de color de un diente",
        "cambios de los dientes",
        "cambios en el pezón",
        "caries",
        "carraspeo",
        "cambio en la escritura",
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad al tragar",
        "dificultad habitual para tragar",
        "dificultad para abrir la boca",
        "dificultad para morder y masticar",
        "dolor de cara",
        "dolor de cara",
        "dolor de cara",
        "dolor de cara",
        "dolor de diente",
        "dolor de dientes insoportable",
        "dolor de dientes que va y viene",
        "dolor de encía",
        "dolor en la boca",
        "dolor en la mandíbula",
        "empaste dental flojo",
        "encías hinchadas",
        "encías rojas",
        "encías sangrantes",
        "lesión del diente",
        "lesiones en la boca",
        "lesiones en la boca",
        "lesiones en la boca",
        "lesiones en la boca",
        "lesiones orales presentes durante menos de 3 semanas",
        "llagas en la boca",
        "mal aliento",
        "mal aliento",
        "mal aliento",
        "mal aliento",
        "poca higiene oral",
        "sabor ácido en la boca",
        "sensación de quemazón en la lengua",
    ],
    "hernias": [
        "abdomen aumentado de tamaño",
        "bulto en el abdomen",
        "distensión abdominal",
        "dolor abdominal intenso",
        "dolor abdominal que va y viene",
    ],
    "enfermedades de la mama": [
        "ampolla de leche en el pezón",
        "arrugas o formación de agujeros en la piel de los pechos",
        "bulto en los pechos",
        "cambios en el pezón",
        "dolor al amamantar",
        "dolor o sensibilidad en el pezón",
        "pezon inflamado",
    ],
    "enfermedades de la prostata": [
        "dolor al orinar",
        "dificultad al orinar",
        "dolor al presionar el escroto",
        "dolor en el escroto",
        "secrecion por el pene",
        "dificultad para retraer el prepucio",
        "bulto en escroto",
        "dolor o hinchazón en el pene",
        "hinchazón de cualquier extremidad inferior",
        "sangrado por el ano",
        "sangrado que no se detiene",
        "dolor en la entrepierna o zona genital",
        "dificultad para comenzar a orinar",
        "incapacidad de detener el flujo de orina",
        "no puede orinar",
    ],
    "enfermedades de la vejiga o las vias urinarias": [
        "dificultad al orinar",
        "dolor ardiente al orinar",
        "dolor leve al orinar",
        "incapacidad de detener el flujo de orina",
        "necesidad urgente de orinar",
        "no puede orinar",
        "orina lechosa",
        "orina oscura",
        "orina roja",
    ],
    "enfermedades del riñon": [
        "orina oscura",
        "orina roja",
        "dolor al orinar",
        "ardor al orinar",
        "dificultad al orinar",
        "hinchazón de cualquier extremidad inferior",
        "edema",
        "náuseas",
        "vómitos",
        "pérdida de apetito",
        "fatiga",
        "debilidad",
    ],
    "enfermedades inflamatorias pelvicas femeninas": [
        "dolor al amamantar",
        "dolor durante o despues del sexo",
        "sangrado vaginal diferente al de la menstruación",
        "secreción vaginal",
        "pizazón vulvovaginal",
        "dolor en la pelvis",
        "dolor en la entrepierna o zona genital",
        "fiebre",
        "dolor abdominal",
        "sangrado",
    ],
    "infecciones de transmision sexual": [
        "dolor al eyacular",
        "dolor durante o despues del sexo",
        "sangrado después del sexo",
        "secrecion por el pene",
        "picazon en el pene",
        "dolor o hinchazón en el pene",
        "ardor o picazón de la parte",
        "llagas o absceso cerca del ano",
        "secreción vaginal",
        "pizazón vulvovaginal",
        "sangrado vaginal diferente al de la menstruación",
    ],
    "trastornos de sangrado menstruales o no menstruales": [
        "sangrado menstrual abundante",
        "sangrado vaginal diferente al de la menstruación",
        "sangrado que no se detiene",
        "sangrado después del sexo",
        "aborto médico en el último mes",
        "antecedente familiar de trastornos de la coagulación",
        "heces con sangre",
    ],
    "trastornos genitales femeninos externos": [
        "dolor durante o despues del sexo",
        "sangrado vaginal diferente al de la menstruación",
        "pizazón vulvovaginal",
        "secreción vaginal",
        "dolor o hinchazón en la parte",
        "ardor o picazón de la parte",
        "cambios en la piel de los pliegues",
        "cambios en la piel",
        "bulto en la piel de más de 1 cm",
        "herida en la piel",
        "costras en la piel",
        "manchas rojas en la piel",
        "ronchas en la piel",
        "alergia en la piel",
        "ampollas en la piel",
        "arrugas o formación de agujeros en la piel de los pechos",
        "disminución de la elasticidad de la piel",
        "piel roja",
        "piel seca",
        "lesiones en la garganta",
    ],
    "trastornos genitales masculinos": [
        "dolor al eyacular",
        "bulto en escroto",
        "dolor al presionar el escroto",
        "dolor en el escroto",
        "dificultad para retraer el prepucio",
        "secrecion por el pene",
        "dolor o hinchazón en el pene",
        "bulto en el pene",
        "picazon en el pene",
        "prepucio pegado detrás de la cabeza del pene",
        "hinchazón de cualquier extremidad inferior",
        "dolor o hinchazón en la parte",
        "huevos hinchados",
    ],
    "trastornos menopausicos o perimenopausicos": [
        "aumento de peso",
        "calambres musculares",
        "cambios en la piel",
        "cambios en la piel de los pliegues",
        "cambios en la piel del cuello",
        "disminución de la elasticidad de la piel",
        "dolor articular",
        "dolor de cabeza que va y viene",
        "dolor de cabeza que va y viene",
        "mareo leve",
        "más sed de lo habitual",
        "menopausia",
        "menstruación anormal",
        "menstruación irregular",
        "pérdida de interés en el sexo",
        "pérdida de peso",
        "piel seca",
        "sofocos",
        "sudoración excesiva",
        "vértigo",
    ],
    "enfermedades del sistema musculo esqueletico o del tejido conjuntivo": [
        "articulación deforme sin traumatismo reciente",
        "articulación difícil de mover",
        "asimetría de la columna",
        "columna rígida en la mañana",
        "cojera",
        "cojera",
        "cojera",
        "cojera",
        "coyunturas duras",
        "debilidad muscular en manos, brazos u hombros",
        "debilidad muscular en pies, piernas o muslos",
        "deformidad de una articulación tras una lesión",
        "dolor al mover el hombro",
        "dolor al mover el tobillo",
        "dolor al mover la cadera",
        "dolor al mover la muñeca",
        "dolor al mover la rodilla",
        "dolor articular",
        "dolor de espalda",
        "dolor de huesos",
        "dolor en las articulaciones",
        "dolor en los músculos",
        "dolor en los tobillos",
        "dolor intenso tras una lesión",
        "fractura o hueso roto",
        "incapacidad de inclinarse hacia adelante",
        "juanete",
        "manos rígidas en la mañana",
        "me crujen las articulaciones",
        "músculos temblorosos",
        "músculos tensos y con espasmos",
        "rigidez articular que se alivia con el ejercicio",
    ],
    "cefalea y migrana": [
        "antecedentes de dolores de cabeza",
        "dolor de cabeza insoportable",
        "dolor de cabeza muy intenso",
        "dolor de cabeza que va y viene",
    ],
    "neuritis y neuralgias": [
        "dolor de cabeza insoportable",
        "dolor de cabeza muy intenso",
        "dolor de cabeza que va y viene",
        "dolor de cara",
        "dolor de cuello",
        "dolor de oídos",
        "dolor de ojos insoportable",
        "dolor de ojos moderado",
        "dolor alrededor o detrás del ojo",
        "dolor en zona de la oreja",
        "hormigueo en los dedos",
        "hormigueo o entumecimiento",
        "cara dormida",
        "calambres en la cara",
        "debilidad muscular en manos, brazos u hombros",
        "debilidad muscular en pies, piernas o muslos",
        "pérdida de la sensibilidad en brazo  y perdida de sensibilida en pierna",
        "visión doble repentina",
    ],
    "vias respiratorias superiores": [
        "antecedente de infección reciente de las vías respiratoria alta",
        "ardor de garganta",
        "carraspeo",
        "carraspeo",
        "carraspeo",
        "carraspeo",
        "congestión o escurrimiento nasal desencadenados por el ambiente",
        "escurrimiento de mocos por detrás de la garganta",
        "escurrimiento nasal",
        "escurrimiento nasal crónico",
        "estornudo",
        "estornudos",
        "estornudos por alergia",
        "garganta roja",
        "moco amarillo o verde por la nariz",
        "moco transparente o blanco por la nariz",
        "nariz tapada",
        "nariz tapada por más de 3 meses",
        "nariz tapada que empeora tras mejoría ligera",
        "sinusitis",
        "tos",
        "tos",
        "tos",
        "tos",
        "tos con flema",
        "tos con sangre",
        "tos de más de ocho semanas",
        "tos por la noche",
        "tos que dura entre 3 y 8 semanas",
        "tos seca",
        "tos seca y con flemas alternante",
    ],
    "enfermedades del ojo, parpado, conjuntivas y vias lagrimales": [
        "ceguera de un ojo",
        "discapacidad visual",
        "discapacidad visual en un ojo",
        "disminución progresiva de la vista",
        "disminución repentina de la vista",
        "dolor alrededor o detrás del ojo",
        "dolor de ojos insoportable",
        "dolor de ojos moderado",
        "dolor en los ojos",
        "dolor en un ojo",
        "hinchazón alrededor de un ojo",
        "ojo rojo",
        "ojo seco",
        "ojos llorosos",
        "ojos saltones",
        "ojos vidriosos",
        "párpados caídos",
        "problemas para cerrar los ojos",
        "secreción ocular",
        "secreción seca en los párpados",
        "temblor en los párpados",
        "visión doble repentina",
    ],
    "diabetes": [
        "aumento de peso",
        "boca seca",
        "más sed de lo habitual",
        "más hambre de lo habitual",
        "pérdida de peso",
        "glucosa muy baja (azucar baja) ahora",
        "antecedente de glucosa muy baja (azucar baja)",
        "visión doble repentina",
        "cansancio respiratorio",
        "infección por helicobacter pylori",
    ],
    "sobrepeso u obesidad": [
        "sobrepeso y obesidad",
        "aumento de peso",
        "diabetes",
        "colesterol alto",
        "hipertensión diagnosticada",
        "enfermedad coronaria diagnosticada",
        "apnea del sueño",
    ],
    "enfermedades infecciosas o parasitarias": [
        "fiebre de duración menor a 3 días",
        "fiebre mas de 3 días",
        "escalofríos",
        "ganglios linfáticos agrandados",
        "ganglios linfáticos dolorosos",
        "herida con pus",
        "herida inflamada",
        "inflamación",
        "infección por helicobacter pylori",
        "lesiones en la garganta",
        "moco amarillo o verde por la nariz",
        "moco transparente o blanco por la nariz",
        "picadura de abeja",
        "picadura de alacran",
        "picadura de insecto",
        "picadura de insecto desconocido",
        "picadura de mosquito",
        "piel roja",
        "placas blancas en las amígdalas",
        "secreción por el oído",
        "tos con flema",
        "tos con sangre",
        "úlcera",
        "vómito",
    ],
    "trastornos mentales, del comportamiento y del neurodesarrollo": [
        "aceleración del pensamiento y el habla",
        "ansiedad",
        "antecedente de episodio depresivo",
        "cambio en la escritura",
        "comportamiento compulsivo",
        "comportamientos motores repetitivos involuntarios",
        "confusión o desorientación repentina",
        "convulsiones",
        "depresión",
        "desorientación o confusión que dura más de una semana",
        "dificultad para hablar o entender  repentina",
        "dificultad para hablar o entender habitual",
        "miedo a perder el control",
        "músculos temblorosos",
        "músculos tensos y con espasmos",
        "necesidad de mover las piernas en la noche",
        "pensamientos obsesivos",
        "pérdida de interés en el sexo",
        "pérdida de la consciencia",
        "pérdida de la voz",
        "pérdida del equilibrio",
        "pesimismo",
        "problemas para completar tareas",
        "problemas para concentrarse",
        "temblores de cabeza",
        "temblores durante el movimiento",
        "temblores en ambas manos",
        "temblores que empeoran con el estrés",
        "vértigo",
    ],
    "traumatismos, intoxicaciones u otras consecuencias de causas externas": [
        "caída accidental reciente",
        "choque eléctrico",
        "cirugía hace más de 2 semanas",
        "cirugía hace menos de 2 semanas",
        "comer carnes crudas o mal cocidas",
        "deformidad de una articulación tras una lesión",
        "golpe en la cabeza",
        "herida autoinfligida",
        "herida con pus",
        "herida en la piel",
        "herida inflamada",
        "herida que no cura",
        "lesión de la muñeca",
        "lesión del diente",
        "lesión del hombro",
        "lesión en accidente vehicular",
        "lesión en el pie",
        "lesión en la rodilla",
        "lesión menor de pliegue de la uña",
        "lesión oral menor a 1 cm",
        "lesión oral única",
        "mordedura por animal",
        "moretón",
        "moretón después de una lesión",
        "múltiples lunares o marcas de nacimiento",
        "objeto tragado",
        "picadura de abeja",
        "picadura de alacran",
        "picadura de insecto",
        "picadura de insecto desconocido",
        "picadura de mosquito",
        "quemadura en la piel",
        "quemadura por el sol",
        "quemadura severa",
        "quemadura severa de piel",
        "síntomas relacionados a lesión reciente",
        "tirar o jalar de su propia oreja",
    ],
    "dermatitis y eczema": [
        "alergia en la piel",
        "ampollas en la piel",
        "ardor o picazón de la parte",
        "arrugas o formación de agujeros en la piel de los pechos",
        "cambios en la piel",
        "cambios en la piel de los pliegues",
        "costras en la piel",
        "disminución de la elasticidad de la piel",
        "erupciones en la piel",
        "herida en la piel",
        "hinchazón en la piel",
        "inflamación",
        "lesiones en la piel",
        "manchas rojas en la piel",
        "piel roja",
        "piel seca",
        "picazón",
        "ronchas en la piel",
        "quemadura en la piel",
        "quemadura por el sol",
    ],
    "infecciones y parasitosis de la piel y tcs": [
        "alergia en la piel",
        "ampollas en la piel",
        "costras en la piel",
        "cambios en la piel",
        "cambios en la piel de los pliegues",
        "erupciones en la piel",
        "espinillas",
        "herida en la piel",
        "herida inflamada",
        "hinchazón en la piel",
        "inflamación",
        "inflamación",
        "inflamación",
        "inflamación",
        "lesiones en la boca",
        "lesiones en la boca",
        "lesiones en la boca",
        "lesiones en la boca",
        "manchas rojas en la piel",
        "moretón",
        "picadura de insecto",
        "picadura de insecto desconocido",
        "picazón",
        "piel roja",
        "ronchas en la piel",
        "quemadura en la piel",
        "úlcera",
        "puntos negros",
    ],
    "enfermedades del pulmon": [
        "cansancio respiratorio",
        "chillido en el pecho",
        "crisis de asma",
        "dificultad para respirar al hacer mucho esfuerzo",
        "dificultad para respirar al hacer pequeño esfuerzo",
        "dificultad para respirar durante el sueño",
        "dificultad para respirar en la noche",
        "falta de aire al hacer mediano esfuerzo",
        "falta de aire al hacer pequeño esfuerzo",
        "tos",
        "tos",
        "tos",
        "tos",
        "tos con flema",
        "tos con sangre",
        "tos de más de ocho semanas",
        "tos por la noche",
        "tos que dura entre 3 y 8 semanas",
        "tos seca",
        "tos seca y con flemas alternante",
        "asma diagnosticado",
        "enfermedad pulmonar obstructiva crónica diagnosticada",
    ],
    "vias respiratorias bajas": [
        "cansancio respiratorio",
        "chillido en el pecho",
        "dificultad para respirar al hacer mucho esfuerzo",
        "dificultad para respirar al hacer pequeño esfuerzo",
        "dificultad para respirar durante el sueño",
        "dificultad para respirar en la noche",
        "falta de aire al hacer mediano esfuerzo",
        "falta de aire al hacer pequeño esfuerzo",
        "respiracion entrecortada",
        "tos",
        "tos",
        "tos",
        "tos",
        "tos con flema",
        "tos con sangre",
        "tos de más de ocho semanas",
        "tos por la noche",
        "tos que dura entre 3 y 8 semanas",
        "tos seca",
        "tos seca y con flemas alternante",
        "asma diagnosticado",
        "crisis de asma",
        "enfermedad pulmonar obstructiva crónica diagnosticada",
    ],
    "tumores de la piel y tcs": [
        "bulto en la piel de más de 1 cm",
        "lunar o marca de nacimiento irregular",
        "múltiples lunares o marcas de nacimiento",
        "masa suave en la piel",
        "ulcera",
        "cambios en la piel",
        "arrugas o formación de agujeros en la piel de los pechos",
        "costras en la piel",
        "lesiones en la boca",
        "herida que no cura",
        "cambios en la piel de los pliegues",
        "pigmentación marrón de la uña",
        "bulto en los pechos",
    ],
    "tumores genitales femeninos": [
        "bulto en los pechos",
        "cambios en el pezón",
        "dolor o sensibilidad en el pezón",
        "bulto en la piel de más de 1 cm",
        "secreción vaginal",
        "sangrado vaginal diferente al de la menstruación",
        "dolor en la entrepierna o zona genital",
        "menstruación anormal",
        "menstruación irregular",
        "período atrasado",
        "período irregular",
        "aumento de peso",
        "pérdida de peso",
        "cambios en la piel",
        "úlcera",
    ],
    "sintomas generales": [
        "malestar general",
        "escalofríos",
        "fiebre de duración menor a 3 días",
        "fiebre mas de 3 días",
        "fatiga",
        "aumento de peso",
        "pérdida de peso",
        "cansancio respiratorio",
        "pérdida de apetito",
        "náuseas",
        "vómitos",
        "diarrea",
        "estreñimiento",
        "dolor de cabeza",
        "dolor muscular",
        "dolor articular",
        "dolor abdominal",
        "hinchazón",
        "debilidad",
        "vértigo",
        "mareo",
        "desmayo",
        "confusión",
        "desorientación",
        "pérdida de la consciencia",
        "somnolencia",
        "irritabilidad",
        "ansiedad",
        "depresión",
        "inquietud",
        "insomnio",
        "pérdida de interés en el sexo",
        "pérdida de memoria",
        "dificultad para concentrarse",
        "problemas para dormir",
        "sudoración excesiva",
        "sudoración nocturna",
        "piel fría y pegajosa",
        "piel seca",
        "piel amarilla",
        "cambios en la piel",
        "picazón",
        "manchas rojas en la piel",
        "ronchas en la piel",
        "ampollas en la piel",
        "heridas en la piel",
        "ganglios linfáticos inflamados",
        "ganglios linfáticos dolorosos",
    ],
    "tumores malignos": [
        "antecedente de cáncer",
        "bulto en el abdomen",
        "bulto en la piel de más de 1 cm",
        "bulto en los pechos",
        "cambio en la escritura",
        "ganglios linfáticos agrandados",
        "lunar o marca de nacimiento irregular",
        "múltiples lunares o marcas de nacimiento",
        "pérdida de peso",
        "pérdida de peso",
    ],
    "tumores mama": [
        "bulto en los pechos",
        "bulto de menos de 1 cm",
        "arrugas o formación de agujeros en la piel de los pechos",
        "cambios en el pezón",
        "dolor o sensibilidad en el pezón",
        "pezon inflamado",
    ],
}
