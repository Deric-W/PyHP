#!/usr/bin/python3

"""tests for pyhp.wsgi.interfaces.phputils"""

import os
import io
import sys
import unittest
import tempfile
from pyhp.wsgi.interfaces import phputils
from werkzeug.datastructures import FileStorage


class TestCallbackQueue(unittest.TestCase):
    """tests for CallbackQueue"""

    def test_execute(self) -> None:
        """test CallbackQueue.execute"""
        queue = phputils.CallbackQueue()
        results = []
        queue.append((lambda x: results.append(x), [1], {}))
        queue.append((lambda: results.append(2), [], {}))
        queue.append((lambda x: results.append(x), [3], {}))
        queue.execute()
        self.assertEqual(results, [3, 2, 1])

    def test_exception(self) -> None:
        """test behavior on callback exceptions"""
        queue = phputils.CallbackQueue()
        results = []
        queue.append((lambda x: results.append(x), [1], {}))
        queue.append((lambda: results.append(x), [], {}))   # raises NameError
        queue.append((lambda x: results.append(x), [3], {}))
        with self.assertRaises(NameError):
            queue.execute()
        self.assertEqual(results, [3])
        queue.execute()
        self.assertEqual(results, [3, 1])


class TestUploadStreamFactory(unittest.TestCase):
    """tests for UploadStreamFactory"""

    def test_eq(self) -> None:
        """test UploadStreamFactory.__eq__"""
        factories = [
            phputils.UploadStreamFactory("test1"),
            phputils.UploadStreamFactory("test1", 42),
            phputils.UploadStreamFactory("test2"),
        ]
        self.assertEqual(factories[0], factories[0])
        self.assertNotEqual(factories[0], factories[1])
        self.assertNotEqual(factories[0], factories[2])
        self.assertNotEqual(factories[0], 42)

    def test_call(self) -> None:
        """test UploadStreamFactory.__call__"""
        with tempfile.TemporaryDirectory() as directory, \
                tempfile.NamedTemporaryFile(dir=directory):     # simulate other temporary files
            factory1 = phputils.UploadStreamFactory(directory)
            factory2 = phputils.UploadStreamFactory(directory, 2)
            self.assertEqual(factory2.count_files(), 0)
            with factory1() as stream1:
                self.assertNotIsInstance(stream1, phputils.FailedStream)
                self.assertTrue(stream1.name.startswith(directory))
                self.assertEqual(factory2.count_files(), 1)
                with factory2() as stream2:
                    self.assertNotIsInstance(stream2, phputils.FailedStream)
                    self.assertTrue(stream2.name.startswith(directory))
                    with factory2() as stream3:
                        self.assertIsInstance(stream3, phputils.FailedStream)
                        self.assertEqual(stream3.reason, phputils.UploadError.MAX_FILES)
                    with factory1() as stream4:
                        self.assertNotIsInstance(stream4, phputils.FailedStream)
            for file in (stream1, stream2, stream4):
                os.unlink(file.name)


class TestNullStreamFactory(unittest.TestCase):
    """tests for NullStreamFactory"""

    def test_eq(self) -> None:
        """test NullStreamFactory.__eq__"""
        factory = phputils.NullStreamFactory()
        self.assertEqual(
            factory,
            phputils.NullStreamFactory()
        )
        self.assertNotEqual(factory, 42)

    def test_call(self) -> None:
        """test NullStreamFactory.__call__"""
        stream = phputils.NullStreamFactory()()
        self.assertIsInstance(stream, phputils.FailedStream)
        self.assertEqual(stream.reason, phputils.UploadError.DISABLED)


class TestFilesType(unittest.TestCase):
    """tests for FilesType"""

    def test_eq(self) -> None:
        """test FilesType.__eq__"""
        with open(os.devnull, "rb") as stream:
            storage1 = FileStorage(stream)
            storage2 = FileStorage(sys.stdout.buffer)
            self.assertEqual(
                phputils.FilesType(storage1),
                phputils.FilesType(storage1)
            )
            self.assertNotEqual(
                phputils.FilesType(storage1),
                phputils.FilesType(storage2)
            )
            self.assertNotEqual(
                phputils.FilesType(storage1),
                42
            )

    def test_attributes(self) -> None:
        """test FilesType attributes"""
        stream = tempfile.NamedTemporaryFile("rb", delete=False)
        try:
            file = phputils.FilesType(
                FileStorage(
                    stream,
                    filename="upload.test",
                    content_type="test/plain; charset=utf-8"
                )
            )
            self.assertEqual(file.name, "upload.test")
            self.assertEqual(file.type, "test/plain")
            self.assertEqual(file.size, 0)
            self.assertEqual(file.tmp_name, stream.name)
            self.assertEqual(file.error, phputils.UploadError.SUCCESS.value)
        except BaseException:
            stream.close()
            os.unlink(stream.name)
            raise
        else:
            file.close()
            self.assertFalse(os.path.exists(stream.name))

        file = phputils.FilesType(
            FileStorage(
                phputils.FailedStream(phputils.UploadError.UNKNOWN)
            )
        )
        self.assertEqual(file.name, None)
        self.assertEqual(file.type, "")
        self.assertEqual(file.size, 0)
        self.assertEqual(file.tmp_name, "")
        self.assertEqual(file.error, phputils.UploadError.UNKNOWN.value)

    def test_getitem(self) -> None:
        """test FilesType.__getitem__"""
        stream = tempfile.NamedTemporaryFile("rb", delete=False)
        try:
            file = phputils.FilesType(
                FileStorage(
                    stream,
                    filename="upload.test",
                    content_type="test/plain"
                )
            )
            for attribute in ("name", "type", "size", "tmp_name", "error"):
                self.assertEqual(file[attribute], getattr(file, attribute))
            with self.assertRaises(KeyError):
                file["asjdahdashdsohosh"]
        finally:
            os.unlink(stream.name)

    def test_close(self) -> None:
        """test FilesType.close"""
        stream = tempfile.NamedTemporaryFile("rb", delete=False)
        try:
            phputils.FilesType(
                FileStorage(
                    stream,
                    filename="upload.test",
                    content_type="test/plain"
                )
            ).close()
            self.assertFalse(os.path.exists(stream.name))
        except BaseException:
            try:
                os.unlink(stream.name)
            except FileNotFoundError:
                pass
            raise

        phputils.FilesType(
            FileStorage(
                phputils.FailedStream(phputils.UploadError.DISABLED),
                filename="upload.test",
                content_type="test/plain"
            )
        ).close()

        stream = io.BytesIO()
        stream.name = "./aaaaaaaaaaaaaaaaaaaaaaaaaaaaa"   # does not exist
        phputils.FilesType(
            FileStorage(
                stream,
                filename="upload.test",
                content_type="test/plain"
            )
        ).close()
