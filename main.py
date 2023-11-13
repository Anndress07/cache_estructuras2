import numpy as np


# Funcion que construye la matriz que representan el cache de tamaño (index, linea cache*numero ways)
# Recibe: tuple "data" con la información de tamaño de linea, index, numero de ways y tamaño de cache
# Retorna: matriz (index, linea cache*numero ways)
def buildCache(data):
    linea, index, ways, cache_size = data
    cache = np.zeros((index, linea*ways))
    return cache

# funcion que, dada las especificaciones del tamaño de cache, calcula la cantidad de bits necesarios
# para direcciones (tag, index, block offset)
# Recibe: tuple "data" con la información de tamaño de linea, index, numero de ways y tamaño de cache
# Retorna: cantidades de bits para block offset, index, tag
def tagBlockBits(cache):
    linea, index, ways, cache_size = cache
    block_offset_bits = np.log2(linea)
    index_bits = np.log2(index)
    tag_bits = 32 - block_offset_bits - index_bits
    print(block_offset_bits, index_bits, tag_bits)
    return block_offset_bits, index_bits, tag_bits


# Función principal que se encarga de leer el trace e ir escribiendo las direcciones en el cache
# Recibe: matriz del cache, información de la cantidad de bits para direccion, y tamaño del way
# Retorna: cache escrita, archivo logfile
def processTrace(cache, data, address_bits, way_size, optimization=False):

    linea, index, ways, cache_size = data
    # creación de máscaras para obtener tag, index y block offset dada la dirección
    block_offset_bits, index_bits, tag_bits = int(address_bits[0]), int(address_bits[1]), int(address_bits[2])
    mask_block_offset = (1 << block_offset_bits) - 1
    mask_index_bits   = ((1 << index_bits) - 1) << block_offset_bits
    mask_tag_bits     = ((1 << tag_bits) - 1) << (block_offset_bits + index_bits)

    i = 0
    way_predictor = 0
    with open('trace.out', 'r') as file:
        with open("logfile.txt", "w") as logfile:
            queue_LRU = []                  # Lista que guarda los primeros elementos, para el reemplazo de LRU
            misses = 0                      # Variable que guarda la cantidad de misses
            hits = 0                        # Variable que guarda la cantidad de hits
            reemplazos = 0                  # Variable que guarda la cantidad de reemplazos
            
            for line in file:
                i = i + 1
                #print(i)
                if (i % 500000 == 0):
                    print(f"Counter: {i}")
                if (i < 10e38):
                    #print(line)
                    line_splitted = line.split()
                    instruction_type = int(line_splitted[1])  # tipo de instrucción: 0 = load, 1 = store
                    address_value = int(line_splitted[2], 16) # dirección
                    address_hex = hex(address_value)          # convertir direcc. a hex
                    instruction_quant = int(line_splitted[3]) # cantidad de instrucciones
                    #print(address_hex)

                    # aplicar mascaras para obtener las direcciones
                    block_number = (address_value & mask_block_offset)
                    index_number = (address_value & mask_index_bits) >> block_offset_bits
                    tag_number = (address_value & mask_tag_bits) >> (block_offset_bits + index_bits)

                    # print(f"address_value: {address_hex}")
                    # print(f"tag: {tag_number}")
                    # print(f"index: {index_number}")
                    # print(f"block: {block_number}")

                    #print("block: ", hex(block_number))
                    #print("index: ", hex(index_number))
                    #print("tag: ", hex(tag_number))

                    # empezar a llenar el cache
                    # 1. revisar que el elemento exista en algun way, viendo tag e index
                    # 2. si no existe y hay espacio en la cache, se mete la linea
                    # 3. si no existe y no hay espacio, se reemplaza
                    way_iterador = 0                # recorre los ways ascendentemente
                    
                    parar = False
                    parar1 = False
                    parar2 = False
                    if optimization == False:
                        # Ciclo while para verificar si ya existe el elemento
                        while not parar1:
                            if (cache[index_number][way_iterador*linea ]) == tag_number:
                                parar = True
                                parar1 = True
                                hit = 1
                            else:
                                way_iterador = way_iterador + 1
                                if way_iterador >= way_size:
                                    parar1 = True
                                hit = 0
                        hits += (instruction_quant - 1) + hit
                        if(hit == 0):
                            misses += 1
                        way_iterador = 0
                    else: 
                        # Ciclo while para verificar si existe el elemento, utilizando la optimización avanzada
                        while not parar1:
                            if (cache[index_number][way_predictor*linea ]) == tag_number:
                                parar = True
                                parar1 = True
                                hit = 1
                            else:
                                way_predictor = 0
                                while not parar2:
                                    if (cache[index_number][way_predictor*linea ]) == tag_number:
                                        parar = True
                                        parar1 = True
                                        parar2 = True
                                        hit = 1
                                    else:
                                        way_predictor = way_predictor + 1
                                        if way_predictor >= way_size:
                                            parar1 = True
                                            parar2 = True
                                            way_predictor = way_predictor=-1
                                        hit = 0
                            hits += (instruction_quant - 1) + hit
                            if(hit == 0):
                                misses += 1
                            way_iterador = way_predictor                               
                    while not parar:

                        # se comprobo que el elemento no existe en el cache, por lo tanto hay que escribirlo
                        if cache[index_number][way_iterador*linea + 1 : ((way_iterador + 1) * linea) - 1 ].all() == 0:
                            cache[index_number][way_iterador*linea] = tag_number        # se escribe tag en cache
                            cache[index_number][way_iterador*linea + 1: ((way_iterador + 1) * linea) - 1] = 1   # se escribe 1 en toda la linea
                            queue_LRU.append((index_number, way_iterador))  # se añade el elemento a la lista de LRU para el reemplazo
                            #print(f"linea puesta en {index_number}, way: {way_iterador}")
                            parar = True
                        else:
                            way_iterador = way_iterador + 1
                            # si iteramos en todos los ways y no hay espacio, hay que reemplazar
                            # reemplazamos el primer elemento de la lista queue_LRU, y luego lo borramos de la lista
                            if way_iterador >= way_size:
                                parar = True
                                way_iterador = 0
                                # reemplazo con el primer elemento con el index respectivo en queue_LRU
                                lru_index = [y[0] for y in queue_LRU].index(index_number)

                                cache[(queue_LRU[lru_index])[0]][(queue_LRU[lru_index])[1] * linea] = tag_number
                                # cache[0][0 * 32 + 1 : ((0 + 1)*32 ) - 1] = cache[5][1 : 31]
                                cache[(queue_LRU[lru_index])[0]][(queue_LRU[lru_index])[1] * linea + 1: (((queue_LRU[lru_index])[1] + 1) * linea) - 1] = 1
                                #print(f"linea puesta en {(queue_LRU[0])[0]}, way: {(queue_LRU[0])[1]}")
                                queue_LRU.append(((queue_LRU[lru_index])[0], (queue_LRU[lru_index])[1]))    # pongo nueva escritura al final
                                queue_LRU.pop(lru_index)                                            # borro primer elemento
                                reemplazos += 1



                #print(queue_LRU)
                #print((queue_LRU[0])[0])
            HMR = [hits, misses, reemplazos]
            for row1 in cache:
                # Convert each element to a string and join them with a space
                row_str = ' '.join(map(str, row1))

                # Write the row to the file followed by a newline
                logfile.write(row_str + '\n')







    return HMR


if __name__ == '__main__':
    #especificaciones_cache = getValues()
    data = 32, 256, 4, 32768
    #data = 64, 128, 16, 131072
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 4
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))
    #print(data)


# A continuación se muestra el análisis comparativo.

# Prueba 1. Línea de cache 64 bytes, 16 ways. Barrido de tamaño: 32, 64, 128KB. 
    print("Prueba 1. Línea de cache 64 bytes, 16 ways. Barrido de tamaño: 32, 64, 128KB.")

    # (CON OPTIMIZACIÓN).
    #Tamaño 32
    data = 32, 64, 16, 32768
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Tamaño 32:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Tamaño 64
    data = 64, 64, 16, 65536
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Tamaño 64:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Tamaño 128KB
    data = 128000, 64, 16, 131072000
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Tamaño 128KB:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

# (SIN OPTIMIZACIÓN).

    #Tamaño 32
    data = 32, 64, 16, 32768
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Tamaño 32:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Tamaño 64
    data = 64, 64, 16, 65536
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Tamaño 64:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Tamaño 128KB
    data = 128000, 64, 16, 131072000
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Tamaño 128KB:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

# Prueba 2. Tamaño 32KB, línea de cache 64 bytes. Barrido de asociatividad: 4, 8, 16.
    print("Prueba 2. Tamaño 32KB, línea de cache 64 bytes. Barrido de asociatividad: 4, 8, 16.")

    # (CON OPTIMIZACIÓN).
    #Way 4
    data = 32768, 64, 4, 8388608
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 4
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Way 4:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Way 8
    data = 32768, 64, 8, 16777216
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Way 8:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Way 16
    data = 32768, 64, 16, 33554432
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Way 16:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

# (SIN OPTIMIZACIÓN).

    #Way 4
    data = 32768, 64, 4, 8388608
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 4
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Way 4:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Way 8
    data = 32768, 64, 8, 16777216
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Way 8:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Way 16
    data = 32768, 64, 16, 33554432
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 16
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Way 16:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

# Prueba 3. Tamaño 32KB, asociatividad 8 ways. Barrido de línea de cache: 32, 64 y 128 bytes
    print("Prueba 3. Tamaño 32KB, asociatividad 8 ways. Barrido de línea de cache: 32, 64 y 128 bytes.")

# (CON OPTIMIZACIÓN).

    #Linea de cache 32
    data = 32768, 32, 8, 8388608
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Línea de cache 32:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Linea de cache 64
    data = 32768, 64, 8, 16777216
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Línea de cache 64:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Linea de cache 128
    data = 32768, 128, 8, 33554432
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, True)
    print("Con optimización - Línea de cache 128:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

# (SIN OPTIMIZACIÓN).

    #Linea de cache 32
    data = 32768, 32, 8, 8388608
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Línea de cache 32:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Linea de cache 64
    data = 32768, 64, 8, 16777216
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Línea de cache 64:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))

    #Linea de cache 128
    data = 32768, 128, 8, 33554432
    cache = buildCache(data)
    address_bits = tagBlockBits(data)
    way_size = 8
    HMR = processTrace(cache,data, address_bits, way_size, False)
    print("Sin optimización - Línea de cache 128:")
    print("Se tuvieron ", HMR[0], "hits")
    print("Se tuvieron ", HMR[1], "misses")
    print("Se tuvieron ", HMR[2], "reemplazos")
    print(np.shape(cache))
    