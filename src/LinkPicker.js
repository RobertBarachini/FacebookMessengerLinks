let linksObjectArray = null;
let currentPage = 0;
const itemsPerPage = 100; // 100
let isUnsaved = false;

const colorDeselected = '#e76d4f';
const colorSelected = '#4FE7C5';

//
//// DB STUFF
//

// Adapted from https://gist.github.com/JamesMessinger/a0d6389a5d0e3a24814b - thank you!
// The official documentation has too much overhead and is cumbersome at best. It made me question some stuff.
// This solution resembles some type of pasta but it gets the job done

const saveLargeObject = async (key, value) => {
	// This works on all devices/browsers, and uses IndexedDBShim as a final fallback 
	const indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;
	// Open (or create) the database
	const open = indexedDB.open("MyDatabase", 1);
	
	// Create the schema
	open.onupgradeneeded = function() {
		const db = open.result;
		const store = db.createObjectStore("MyObjectStore", {keyPath: "key"});
		var index = store.createIndex("KeyIndex", "key");
	};
	
	open.onsuccess = function() {
		// Start a new transaction
		const db = open.result;
		const tx = db.transaction("MyObjectStore", "readwrite");
		const store = tx.objectStore("MyObjectStore");
		const index = store.index("KeyIndex");

		// Add some data
		store.put({ key, value });
		console.log('Saved large object.');
		alert("Data saved successfully")

		// Close the db when the transaction is done
		tx.oncomplete = function() {
			db.close();
		};
	}
}

const loadLargeObject = async (key) => {
	// This works on all devices/browsers, and uses IndexedDBShim as a final fallback 
	const indexedDB = window.indexedDB || window.mozIndexedDB || window.webkitIndexedDB || window.msIndexedDB || window.shimIndexedDB;
	// Open (or create) the database
	const open = indexedDB.open("MyDatabase", 1);
	
	// Create the schema
	open.onupgradeneeded = function() {
		const db = open.result;
		const store = db.createObjectStore("MyObjectStore", {keyPath: "key"});
		var index = store.createIndex("KeyIndex", "key");
	};

	open.onsuccess = function() {
		// Start a new transaction
		const db = open.result;
		const tx = db.transaction("MyObjectStore", "readwrite");
		const store = tx.objectStore("MyObjectStore");
		const index = store.index("KeyIndex");
		
		// Query the data
		const getRes = index.get(key);//store.get(key);

		getRes.onsuccess = function() {
			// return getRes.result.value;
			linksObjectArray = getRes.result.value;
			initSite();
			createPage();
			updatePageStatus();
		};

		// Close the db when the transaction is done
		tx.oncomplete = function() {
			db.close();
		};
	}
}
//
//// DB STUFF END
//

async function initSite() {
	currentPage = parseInt(loadObject('currentPage'));
	if(Number.isNaN(currentPage) || currentPage > getMaxPageNum()) {
		currentPage = 0;
	}
	// linksObjectArray = JSON.parse(loadObject('linksObjectArray'));
	if (!linksObjectArray) {
		linksObjectArray = loadLargeObject('linksObjectArray');
	} else {
		createPage();
		updatePageStatus();
	}
}

// Prevent reload / closing when unsaved modivied data is present
window.onbeforeunload = s => isUnsaved ? "" : null;
initSite();

function saveObject(key, value) {
	localStorage.setItem(key, value);
}

function loadObject(key) {
	return localStorage.getItem(key);
}

function saveChanges(event) {
	isUnsaved = false;
	// saveObject('linksObjectArray', JSON.stringify(linksObjectArray));
	saveLargeObject('linksObjectArray', linksObjectArray);
}

function toggleSelected(event) {
	isUnsaved = true;
	const clickedObjId = event.target.id;
	const arrayId = parseInt(clickedObjId.split('_')[1]);
	linksObjectArray[arrayId].selected = !linksObjectArray[arrayId].selected;
	const selectionIndicator = document.getElementById('selected_' + arrayId);
	if (linksObjectArray[arrayId].selected === true) {
		selectionIndicator.classList.remove('deselected');
		selectionIndicator.classList.add('selected');
	} else {
		selectionIndicator.classList.remove('selected');
		selectionIndicator.classList.add('deselected');
	}
	// Comment saveObject in case of bad performance and use the Save changes button
	// saveObject('linksObjectArray', JSON.stringify(linksObjectArray));
}

// https://stackoverflow.com/a/68579016
const findAllOccurrences = (str, substr) => {
  str = str.toLowerCase();
  let result = [];
  let idx = str.indexOf(substr)
  while (idx !== -1) {
    result.push(idx);
    idx = str.indexOf(substr, idx+1);
  }
  return result;
};


// DONE (at LinksParser.py processing stage) TODO: FIX BAD JSON ENCODING
// Facebook JSON contains badly encoded strings that contains
// stuff like \u00c5\u00a0 (this code represents a 'Š' character)
const replaceUnicodeEscapes = (str) => {
	const occurances = findAllOccurrences(str, '\\u');
	let strFixed = str;
	occurances.forEach((occurance) => {
		const uniEscape = str.substr(occurance, 12)
		str = str.replace('')
	});
};

// TODO FIX BAD JSON ENCODING
const getParticipantsNames = (participants) => {
	const names = [];
	participants.forEach((participant) => {
		const recoded = participant.name; // replaceUnicodeEscapes(participant.name);
		names.push(recoded);
	});
	return names.sort();
};

const switchImageForIframe = (event) => {
	const imgObj = event.target;
	const container = event.target.parentNode;
	const arrayId = parseInt(container.parentNode.parentNode.parentNode.id.split('_')[1]);
	if (linksObjectArray[arrayId].youtube_data.items.length != 0) {
		const iframeTemplate = document.createElement('template');
		console.log(linksObjectArray[arrayId].youtube_data);
		const videoId = linksObjectArray[arrayId].youtube_data.items[0].id.toString();
		const iframeString = '<iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/' + videoId + '?autoplay=1" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>';
		iframeTemplate.innerHTML = iframeString;
		container.insertBefore(iframeTemplate.content.firstChild, imgObj);
		container.removeChild(imgObj);
	}
};

const formatDate = (date) => {
	return date.toString().split('(')[0].trim();
};

function createPage() {
	const linksContainer = document.getElementById('linksContainer');
	linksContainer.innerHTML = '';
	for (let i = currentPage * itemsPerPage; i < Math.min(currentPage * itemsPerPage + itemsPerPage, linksObjectArray.length); i++) {
		const obj = linksObjectArray[i];
		const newNode = document.createElement('div');
		newNode.setAttribute('id', 'obj_' + i.toString());
		// newNode.setAttribute('onclick', 'toggleSelected(event)');
		newNode.setAttribute('class', 'container');

		const newNodeData = document.createElement('div');
		newNodeData.setAttribute('class', 'containerData');

		const selectedIndicator = document.createElement('div');
		selectedIndicator.setAttribute('class', 'selectedIndicator');
		selectedIndicator.setAttribute('id', 'selected_' + i.toString());
		newNode.setAttribute('onclick', 'toggleSelected(event)');

		if (obj.selected === true) {
			selectedIndicator.classList.add('selected');
		} else {
			selectedIndicator.classList.add('deselected');
		}
		let basicText = '<span>' + (i + 1).toString() + ": </span>";
		imgSrc = '../res/local/DELETED.jpg';
		if ('img_path' in obj) {
			// TODO save image path and such to the obj itself
			imgSrc = '../' + obj.img_path;
		}
		if (obj.youtube_data.items.length != 0) {
			basicText += obj.youtube_data.items[0].snippet.title;
		} else {
			basicText +=  obj.link;
		}
		newNodeData.innerHTML = '<a href="' + obj.link + '" target="_blank">' + basicText + '</a>';

		const newNodeDataInner = document.createElement('div');
		newNodeDataInner.setAttribute('class', 'containerDataInner');

		const newNodeDataInnerLeft = document.createElement('div');
		newNodeDataInnerLeft.setAttribute('class', 'containerDataInnerLeft');

		const newNodeDataInnerRight = document.createElement('div');
		newNodeDataInnerRight.setAttribute('class', 'containerDataInnerRight');

		newNodeDataInner.appendChild(newNodeDataInnerLeft);
		newNodeDataInner.appendChild(newNodeDataInnerRight);

		newNodeDataInnerLeft.innerHTML += '<img src="' + imgSrc + '" width="320" height="180" onclick="switchImageForIframe(event)" style="cursor: pointer;">';
		newNodeDataInnerRight.innerHTML += '<p><span>Sender name:</span> ' + obj.sender_name + '</p>';
		newNodeDataInnerRight.innerHTML += '<p><span>Chat perticipants:</span> ' + getParticipantsNames(obj.participants).join(', ') + '</p>';
		const date = new Date(obj.timestamp_ms);
		newNodeDataInnerRight.innerHTML += '<p> <span>Sent on:</span> ' + formatDate(date) + '</p>';
		if (obj.video_id != null) {
			newNodeDataInnerRight.innerHTML += '<p><span>Video ID:</span> ' + obj.video_id + '</p>'
		}
		if (obj.playlist_id != null) {
			newNodeDataInnerRight.innerHTML += '<p><span>Playlist ID:</span> ' + obj.playlist_id + '</p>'
		}
		newNodeData.appendChild(newNodeDataInner);
		newNode.appendChild(selectedIndicator);
		newNode.appendChild(newNodeData);
		linksContainer.appendChild(newNode);
	}
}

function updatePageStatus() {
	const maxPageNum = getMaxPageNum();
	const pageStatus = document.getElementById('pageStatus')
	pageStatus.innerText = "Page " + (currentPage + 1).toString() + " / " + (maxPageNum + 1).toString();
}

function getMaxPageNum() {
	let maxPageNum = Infinity;
	if (linksObjectArray != null) {
		maxPageNum = Math.floor(linksObjectArray.length / itemsPerPage);
	}
	return maxPageNum;
}

function changePage(event) {
	const maxPageNum = getMaxPageNum();
	if (event.target.id === 'buttonLeft') {
		if (currentPage > 0) {
			currentPage -= 1;
		}
	}
	if (event.target.id === 'buttonRight') {
		if (currentPage < maxPageNum) {
			currentPage += 1
		}
	}
	saveObject('currentPage', currentPage.toString());
	updatePageStatus();
	createPage();
}

https://stackoverflow.com/a/29176118
function openFile(event) {
	const input = event.target;
	const reader = new FileReader();
	reader.onload = () => {
		const text = reader.result;
		linksObjectArray = JSON.parse(text);
		// saveObject('linksObjectArray', text)
		saveLargeObject('linksObjectArray', linksObjectArray);
		// createPage();
		initSite();
	};
	reader.readAsText(input.files[0]);
};

// https://stackoverflow.com/a/18197511
function download(filename, text) {
	var pom = document.createElement('a');
	pom.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(text));
	pom.setAttribute('download', filename);
	if (document.createEvent) {
		var event = document.createEvent('MouseEvents');
		event.initEvent('click', true, true);
		pom.dispatchEvent(event);
	}
	else {
		pom.click();
	}
}

function downloadClick(event) {
	download('processed_selection.json', JSON.stringify(linksObjectArray, null, 2));
}

// https://www.w3schools.com/howto/howto_js_scroll_to_top.asp
//Get the button:
mybutton = document.getElementById("myBtn");

// When the user scrolls down 20px from the top of the document, show the button
window.onscroll = function() {scrollFunction()};

function scrollFunction() {
  if (document.body.scrollTop > 20 || document.documentElement.scrollTop > 20) {
    mybutton.style.display = "block";
  } else {
    mybutton.style.display = "none";
  }
}

// When the user clicks on the button, scroll to the top of the document
function topFunction() {
  document.body.scrollTop = 0; // For Safari
  document.documentElement.scrollTop = 0; // For Chrome, Firefox, IE and Opera
}
