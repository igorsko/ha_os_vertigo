# Recuperare i parametri del proprio dispositivo

Ogni installatore deve usare **il proprio ID e la propria chiave locale**. Non sono forniti nel repository e non sono condivisibili tra dispositivi diversi. Dopo il recupero, il componente funziona in locale senza account cloud.

## Indirizzo IP e ID

L'indirizzo si trova nell'elenco client del router. Conviene riservarlo tramite DHCP. Home Assistant deve poter raggiungere la rete del Vertigo sulla porta TCP 6668.

Un dispositivo Tuya può annunciare IP, ID e versione sulla rete locale. Con TinyTuya installato, lo script opzionale ascolta gli annunci per circa dieci secondi:

```sh
python -m pip install tinytuya==1.20.0
python tools/discover.py
```

Non recupera la chiave, non invia comandi e non esegue una scansione forzata delle porte. La rilevazione può fallire su reti separate, VLAN o Wi-Fi con isolamento client. L'ID può anche essere presente nei dettagli del dispositivo o nei dati dell'app OS Home; le schermate cambiano secondo la versione.

## Chiave locale: piattaforma Tuya

La procedura cloud di [TinyTuya](https://github.com/jasonacox/tinytuya#setup-wizard---getting-local-keys) richiede un progetto Tuya e il collegamento dell'account che contiene il dispositivo. Funziona solo se la piattaforma permette di collegare quell'app e quell'account.

**OS Home è un'app OEM:** non assumere che le credenziali OS Home siano un account Smart Life/Tuya Smart o che l'associazione tramite QR sia supportata. Il dominio `smart321.com` usato dall'app non costituisce da solo un portale web per ottenere la chiave. La [documentazione Tuya](https://developer.tuya.com/en/docs/app-development/devicemanage?id=Ka6ki8r2rfiuu) descrive `localKey` come chiave per la comunicazione locale del dispositivo.

Non riassociare l'apparecchio a un'altra app soltanto per tentare questa procedura senza considerare che l'associazione corrente e la chiave possono cambiare.

## Alternativa OS Home: emulatore Android autenticato

Metodo sperimentale verificato su una sessione OS Home in emulatore Android. La presenza della chiave in memoria dipende dalla versione dell'app: non è garantita. Non richiede di pubblicare credenziali né di accedere al telefono di altre persone.

1. Installa Android Studio dal sito ufficiale e crea un dispositivo virtuale con immagine **Google Play**, se OS Home richiede i servizi Google.
2. Installa OS Home da una fonte ufficiale, accedi con il tuo account e verifica che il tuo Vertigo sia visibile e controllabile.
3. Apri la pagina del Vertigo affinché l'app carichi i dati del dispositivo. Evita comandi di riscaldamento se non necessari.
4. Individua la seriale dell'emulatore con `adb devices`. Salva uno snapshot con il comando della console Android:

```sh
adb -s <seriale-emulatore> emu avd snapshot save vertigo_key_diag
```

5. Cerca il file `ram.bin` nella cartella `snapshots/vertigo_key_diag` di quel dispositivo virtuale. Posizione tipica su macOS/Linux: `~/.android/avd/<nome>.avd/snapshots/vertigo_key_diag/ram.bin`; su Windows si trova nella cartella AVD dell'utente. Non tutti i formati di snapshot espongono stringhe leggibili.
6. Chiudi OS Home e sospendi altre integrazioni locali del Vertigo, poi usa lo script incluso con il tuo file, ID e indirizzo:

```sh
python tools/recover_key.py --snapshot /percorso/ram.bin \
  --device-id <ID-del-tuo-dispositivo> --host <IP-del-tuo-dispositivo> \
  --output /percorso/privato/vertigo-credentials.json
```

Lo script cerca soltanto candidati `localKey` vicino all'ID indicato. Non stampa le chiavi e accetta un candidato solo dopo una **lettura locale dello stato**, senza accendere o modificare l'apparecchio. Salva il risultato in un nuovo file con permessi 0600 sui sistemi POSIX. Se non trova una chiave valida, non salva nulla. Non funziona su dump cifrati/compressi o se l'app non ha caricato la chiave in memoria.

Uno snapshot RAM può contenere dati dell'account e di altri dispositivi: conservarlo privatamente, non allegarlo a GitHub e cancellarlo quando non serve. Su Windows verificare anche i permessi della cartella di destinazione. Copiare poi i parametri nel modulo Home Assistant.

## Cambio sistema o nuova associazione

Lo stesso dispositivo può essere trasferito a un altro Home Assistant usando ID e chiave ancora validi, con il nuovo IP se necessario. Un reset o una nuova associazione può cambiare la chiave; usare **Riconfigura** per aggiornarla. Non usare contemporaneamente due client locali dello stesso dispositivo durante la verifica.
