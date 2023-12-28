import os
import zipfile
import logging

import tempfile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError


log = logging.getLogger("deepview")

class ProjectUploadSerializer(serializers.Serializer):
    project_archive = serializers.FileField()
    mode = serializers.ChoiceField(choices=["analysis", "time", "memory"], required=True)
    analysis_types = serializers.MultipleChoiceField(choices=[("--all", "All Analysis"),("--measure-breakdown", "Breakdown"), ("--measure-throughput", "Throughput"), ("--habitat-predict", "Habitat predict"), ("--measure-utilization", "Utilization"), ("--energy-compute", "Energy")], required=False)
    exclude_source_files = serializers.ChoiceField(choices=[("include_files", "Add Encrypted Files"), ("exclude_files", "Exclude source files")], default="include_files", required=False)
    entry_point = serializers.CharField(
        max_length=100, required=False, default="entry_point.py"
    )
    output = serializers.ChoiceField(
        choices=["json", "sqlite"], required=False, default="json"
    )

    def create(self, validated_data):
        tmp_dir_obj = tempfile.TemporaryDirectory(prefix="deepview-")
        tmp_dir = tmp_dir_obj.name

        # Save project archive to temp dir
        uploaded_file = validated_data["project_archive"]
        file_path = os.path.join(tmp_dir, uploaded_file.name)

        with open(file_path, "wb") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Unzip project archive
        try:
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(tmp_dir)
        except:
            log.exception(f"Error while unzipping project archive: {file_path}")
            raise ValidationError("Invalid project archive")

        return tmp_dir_obj
    
    def resolve_entry_point_path(self): 
        #Save and unzip project archive
        tmp_dir_obj = self.save()
        tmp_dir = tmp_dir_obj.name

        # Lookup for entry point file 
        entry_point_path = ""
        for root, _, files in os.walk(tmp_dir):
            for file in files: 
                if file == self.validated_data['entry_point']:
                    entry_point_path = os.path.join(root, file)
                    log.debug("Found entry point file: %s", entry_point_path)
                    break

        return entry_point_path
           
