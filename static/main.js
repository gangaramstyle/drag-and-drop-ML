//========================================================================
// Drag and drop image handling
//========================================================================

var r = new Resumable({
  target: '/resumable',
  testChunks: true
});

r.assignDrop(document.getElementById("file-drag"));
r.assignBrowse(document.getElementById("file-upload"));

r.on('fileAdded', function(file) {
  r.upload();
});

r.on('fileSuccess', function(file,message){
  updateTable()
});

r.on('complete', function(){
  console.log("complete")
  document.getElementById("run_btn").hidden = false;
  document.getElementById("clear_btn").hidden = false;
  document.getElementById("csv_btn").hidden = true;
  document.getElementById("run_btn").disabled = false;
  document.getElementById("clear_btn").disabled = false;
  document.getElementById("csv_btn").disabled = true;
});


function runModel() {
  document.getElementById("run_btn").hidden = false;
  document.getElementById("clear_btn").hidden = false;
  document.getElementById("csv_btn").hidden = true;
  document.getElementById("run_btn").disabled = true;
  document.getElementById("clear_btn").disabled = true;
  document.getElementById("csv_btn").disabled = true;
  fetch("/run-model", {
    method: "POST",
    headers: {
      "Content-Length": 0
    }
  })
    .then(resp => {
      if (resp.ok) {
        updateTable();
        document.getElementById("run_btn").hidden = true;
        document.getElementById("clear_btn").hidden = false;
        document.getElementById("csv_btn").hidden = false;
        document.getElementById("run_btn").disabled = true;
        document.getElementById("clear_btn").disabled = false;
        document.getElementById("csv_btn").disabled = false;
      }
    });
}

function clearTable() {
  fetch("/clear-table", {
    method: "POST",
    headers: {
      "Content-Length": 0
    }
  })
    .then(resp => {
      if (resp.ok) {
        updateTable();
        document.getElementById("run_btn").hidden = false;
        document.getElementById("clear_btn").hidden = false;
        document.getElementById("csv_btn").hidden = true;
        document.getElementById("run_btn").disabled = true;
        document.getElementById("clear_btn").disabled = true;
        document.getElementById("csv_btn").disabled = true;
      }
    });
}

function download_table_as_csv(table_id) {
  // Select rows from table_id
  var rows = document.querySelectorAll('table#' + table_id + ' tr');
  // Construct csv
  var csv = [];
  for (var i = 0; i < rows.length; i++) {
      var row = [], cols = rows[i].querySelectorAll('td, th');
      for (var j = 0; j < cols.length; j++) {
          // Clean innertext to remove multiple spaces and jumpline (break csv)
          var data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ')
          // Escape double-quote with double-double-quote (see https://stackoverflow.com/questions/17808511/properly-escape-a-double-quote-in-csv)
          data = data.replace(/"/g, '""');
          // Push escaped string
          row.push('"' + data + '"');
      }
      csv.push(row.join(';'));
  }
  var csv_string = csv.join('\n');
  // Download it
  var filename = 'export_' + table_id + '_' + new Date().toLocaleDateString() + '.csv';
  var link = document.createElement('a');
  link.style.display = 'none';
  link.setAttribute('target', '_blank');
  link.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv_string));
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function fileDragHover(e) {
  // prevent default behaviour
  e.preventDefault();
  e.stopPropagation();

  fileDrag.className = e.type === "dragover" ? "upload-box dragover" : "upload-box";
}

//========================================================================
// Helper functions
//========================================================================

function updateTable() {
  fetch("/inference-status", {
    method: "GET",
  })
    .then(resp => {
      if (resp.ok)
        resp.json().then(data => {
          var headerData = data['header'];
          var bodyData = data['body'];
          if (data['body'].length != 0) {
            // create table if table doesn't exist
            var table = document.getElementById('table');
            if (table === null) {
              table = document.createElement('table');
              table.setAttribute('id', 'table');
              document.getElementById('content-container').append(table);
            }

            // create header if header doesn't exist
            var header = document.getElementById('table-header');
            if (header === null) {
              header = document.createElement('thead');
              header.setAttribute('id', 'table-header');
              table.append(header);

              var headerRow = document.createElement('tr');
              header.append(headerRow);

              for(var i = 0; i < headerData.length; i++) {
                var headerElem = document.createElement('th');
                headerElem.innerHTML = headerData[i];
                headerRow.append(headerElem);
              }
            }


            var body = document.getElementById('table-body');
            if (body === null) {
              body = document.createElement('tbody');
              body.setAttribute('id', 'table-body');
              table.append(body);
            }
            body.innerHTML = "";
            //look, chill, I know  I shouldn't be using the name attribute
            //but it made my life easier
            for(var i = 0; i < bodyData.length; i++) {
              //var rowId = bodyData[i]['rowID'];
              //var updateId = bodyData[i]['updateID'];

              var row = document.createElement('tr');
              //row.setAttribute('id', rowId);
              //row.setAttribute('name', updateId);
              for(var j = 0; j < bodyData[i].length; j++) {
                var cell = document.createElement('td');
                cell.innerHTML = bodyData[i][j];
                row.append(cell);
              }
              body.append(row);
            }
          } else {
            console.log("remove table");
            var table = document.getElementById('table');
            document.getElementById('content-container').removeChild(table);
          }
        });
    })
    .catch(err => {
      console.log("An error occured", err.message);
      window.alert("Oops! Something went wrong.");
    });
}